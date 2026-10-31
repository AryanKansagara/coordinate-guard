"""Independent string oracle and metamorphic checks against the native CLI."""
import argparse
import json
import platform
from pathlib import Path
import random
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'build' / 'coordinate-guard'
INVOCATIONS = 0


def rc(sequence):
    return ''.join({'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}[x] for x in sequence[::-1])


def oracle(sequence, start, reference, alternate, strand='+'):
    """Independent valid-edit oracle; no native code or output is reused."""
    if sequence[start:start + len(reference)] != reference:
        raise ValueError('reference mismatch')
    result = sequence[:start] + alternate + sequence[start + len(reference):]
    return result if strand == '+' else rc(result)


def run_native(args):
    global INVOCATIONS
    INVOCATIONS += 1
    return subprocess.run([str(BINARY), *args], text=True, capture_output=True, timeout=3)


def call(sequence, position, reference, alternate, coordinates='zero', strand='+'):
    result = run_native(['--sequence', sequence, '--position', str(position),
                         '--coordinates', coordinates, '--ref', reference, '--alt', alternate,
                         '--strand', strand])
    content = result.stdout if result.returncode == 0 else result.stderr
    return result.returncode, json.loads(content)


class CoordinateTests(unittest.TestCase):
    def ok(self, sequence, position, reference, alternate, coordinates='zero', strand='+'):
        code, result = call(sequence, position, reference, alternate, coordinates, strand)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output_length'], len(result['sequence']))
        return result

    def error(self, code, *args, **kwargs):
        status, result = call(*args, **kwargs)
        self.assertEqual(status, 2, result)
        self.assertEqual(result['code'], code)

    def test_authored_examples(self):
        for edit in json.loads((ROOT / 'examples' / 'edits.json').read_text()):
            with self.subTest(edit=edit):
                result = self.ok(edit['sequence'], edit['position'], edit['ref'], edit['alt'],
                                 edit['coordinates'], edit['strand'])
                self.assertEqual(result['sequence'], edit['expected'])

    def test_zero_one_equivalence_and_independent_oracle(self):
        rng = random.Random(20261031)
        for _ in range(70):
            sequence = ''.join(rng.choice('ACGT') for _ in range(rng.randrange(1, 35)))
            start = rng.randrange(len(sequence))
            reference, alternate = sequence[start], rng.choice('ACGT')
            zero = self.ok(sequence, start, reference, alternate)
            one = self.ok(sequence, start + 1, reference, alternate, 'one')
            self.assertEqual(zero['sequence'], oracle(sequence, start, reference, alternate))
            self.assertEqual(zero['sequence'], one['sequence'])
            self.assertEqual(zero['forward_interval'], one['forward_interval'])

    def test_insertion_boundary_semantics(self):
        for start in range(5):
            result = self.ok('ACGT', start, '-', 'AA')
            self.assertEqual(result['sequence'], oracle('ACGT', start, '', 'AA'))
            self.assertEqual(result['forward_interval'], [start, start])
            self.assertEqual(result['reference_check'], 'not_applicable_insertion')
            one = self.ok('ACGT', start + 1, '-', 'AA', 'one')
            self.assertEqual(result['sequence'], one['sequence'])

    def test_deletions_including_full_sequence(self):
        for start in range(4):
            for length in range(1, 5 - start):
                ref = 'ACGT'[start:start + length]
                result = self.ok('ACGT', start, ref, '-')
                self.assertEqual(result['sequence'], oracle('ACGT', start, ref, ''))
        self.assertEqual(self.ok('A', 0, 'A', '-', strand='-')['sequence'], '')

    def test_reference_mismatch_is_rejected(self):
        self.error('reference_mismatch', 'ACGT', 1, 'G', 'T')
        self.error('reference_mismatch', 'ACGT', 0, 'AG', '-')

    def test_interval_bounds_and_one_based_zero(self):
        self.error('invalid_position', 'ACGT', 0, 'A', 'T', coordinates='one')
        self.error('out_of_bounds', 'ACGT', 4, 'T', 'A')
        self.error('out_of_bounds', 'ACGT', 3, 'GT', '-')
        self.error('out_of_bounds', 'ACGT', 5, '-', 'A')
        self.error('out_of_bounds', 'ACGT', 18446744073709551615, '-', 'A')

    def test_position_syntax_and_overflow(self):
        for value in ['-1', '+1', '1.0', '1x', '', '9' * 100]:
            self.error('invalid_position', 'ACGT', value, 'A', 'T')

    def test_strict_dna_and_empty_input(self):
        self.error('empty_sequence', '', 0, '-', 'A')
        for sequence in ['acgt', 'ACNT', 'A C', 'AC\nG']:
            self.error('invalid_dna', sequence, 0, 'A', 'T')
        self.error('invalid_dna', 'ACGT', 0, 'A', 'N')

    def test_unsupported_complex_edits_and_empty_alleles(self):
        self.error('unsupported_edit', 'ACGT', 0, 'AC', 'TT')
        self.error('unsupported_edit', 'ACGT', 0, '-', '-')
        self.error('unsupported_edit', 'ACGT', 0, 'A', 'TT')
        self.error('invalid_allele', 'ACGT', 0, '', 'T')

    def test_reverse_complement_twice(self):
        for sequence in ['A', 'ACGT', 'AACCGGTT', 'AGTGCA', 'TTTT']:
            first = self.ok(sequence, 0, sequence[0], sequence[0], strand='-')['sequence']
            second = self.ok(first, 0, first[0], first[0], strand='-')['sequence']
            self.assertEqual(first, rc(sequence))
            self.assertEqual(second, sequence)

    def test_equivalent_edit_on_reverse_complemented_reference(self):
        rng = random.Random(31337)
        for _ in range(35):
            sequence = ''.join(rng.choice('ACGT') for _ in range(12))
            for kind in ['snv', 'insertion', 'deletion']:
                start = rng.randrange(10)
                ref = '' if kind == 'insertion' else sequence[start:start + (2 if kind == 'deletion' else 1)]
                alt = '' if kind == 'deletion' else ('GA' if kind == 'insertion' else rng.choice('ACGT'))
                forward = self.ok(sequence, start, ref or '-', alt or '-')['sequence']
                reverse_start = len(sequence) - start - len(ref)
                reverse = self.ok(rc(sequence), reverse_start, rc(ref) or '-', rc(alt) or '-')['sequence']
                self.assertEqual(reverse, rc(forward))
                self.assertEqual(forward, oracle(sequence, start, ref, alt))

    def test_off_by_one_negative_baseline(self):
        # Both adjacent reference bases are A: a naive REF check would not catch this.
        result = self.ok('AAAA', 2, 'A', 'C', coordinates='one')['sequence']
        naive_no_coordinate_conversion = 'AAAA'[:2] + 'C' + 'AAAA'[3:]
        self.assertEqual(result, 'ACAA')
        self.assertEqual(naive_no_coordinate_conversion, 'AACA')
        self.assertNotEqual(result, naive_no_coordinate_conversion)

    def test_provenance_keeps_forward_interval_on_reverse_output(self):
        result = self.ok('AACCGG', 2, 'CC', '-', strand='-')
        self.assertEqual(result['forward_interval'], [2, 4])
        self.assertEqual(result['output_strand'], '-')
        self.assertEqual(result['original_length'], 6)
        self.assertEqual(result['reference_check'], 'matched')
        self.assertEqual(result['kind'], 'deletion')

    def test_cli_parser_rejects_ambiguous_contracts(self):
        self.error('invalid_coordinates', 'ACGT', 1, 'C', 'T', coordinates='vcf')
        self.error('invalid_strand', 'ACGT', 1, 'C', 'T', strand='reverse')
        for args in [[], ['--unknown', 'x'], ['--sequence'],
                     ['--sequence', 'A', '--sequence', 'A']]:
            result = run_native(args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)['code'], 'invalid_arguments')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CoordinateTests)
    start = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    elapsed = time.perf_counter() - start
    if args.report:
        compiler = subprocess.check_output(['c++', '--version'], text=True).splitlines()[0]
        report = {'schema_version': 1, 'recorded_on': '2026-10-31',
                  'environment': {'platform': platform.platform(), 'python': platform.python_version(), 'compiler': compiler},
                  'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                  'native_cli_invocations': INVOCATIONS,
                  'wall_seconds_including_process_launches': round(elapsed, 6),
                  'data': 'authored and seeded synthetic DNA fixtures',
                  'scope': 'sequence/coordinate transformation only; not inference, biology or clinical validation',
                  'seeds': [20261031, 31337], 'all_passed': result.wasSuccessful()}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    sys.exit(0 if result.wasSuccessful() else 1)
