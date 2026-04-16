# Main application module.
# FEATURE: Demo Fixture.
class Greeter:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def greet(self, person: str) -> str:
        return f"{self.prefix}, {person}!"


def make_message(person: str) -> str:
    greeter = Greeter("Hello")
    return greeter.greet(person)
