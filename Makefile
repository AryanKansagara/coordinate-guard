CXX ?= c++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude
TARGET := build/coordinate-guard

.PHONY: all test evaluate clean
all: $(TARGET)

$(TARGET): src/main.cpp src/coordinate_guard.cpp include/coordinate_guard.hpp
	mkdir -p build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) src/main.cpp src/coordinate_guard.cpp -o $(TARGET)

test: $(TARGET)
	python3 tests/test_guard.py

evaluate: $(TARGET)
	python3 tests/test_guard.py --report benchmarks/local-verification.json

clean:
	rm -rf build
