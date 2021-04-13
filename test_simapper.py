#!/usr/bin/env python3
import simapper

def run():
    simapper.MAP_DIR = "map"
    simapper.run("test.txt", once=True)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Test simapper')
    _args = parser.parse_args()

    run()

if __name__ == "__main__":
    main()
