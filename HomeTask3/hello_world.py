#!/usr/bin/env python3
"""
hello_world.py — Metaflow "Hello World" test pipeline
Run:  python hello_world.py run
"""

from metaflow import FlowSpec, step


class HelloWorldFlow(FlowSpec):

    @step
    def start(self):
        print("Hello from Metaflow! Pipeline started.")
        self.message = "Hello, World!"
        self.next(self.say_hello)

    @step
    def say_hello(self):
        print(self.message)
        self.next(self.end)

    @step
    def end(self):
        print("Pipeline finished successfully.")


if __name__ == "__main__":
    HelloWorldFlow()
