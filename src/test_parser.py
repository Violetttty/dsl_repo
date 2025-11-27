import os
from dsl_parser import parse_text, ParseError, pretty_print_script


# Utility to load a DSL file
def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# === Test 1: parser loads a valid DSL file without errors ===
def test_valid_file():
    print("=== Test 1: Valid DSL file ===")
    text = load("demo1.dsl")
    try:
        script = parse_text(text)
        print("PASS: demo1.dsl parsed successfully.")
        pretty_print_script(script)
    except Exception as e:
        print("FAIL: demo1.dsl should be valid.")
        raise e


# === Test 2: all referenced steps exist ===
def test_references():
    print("\n=== Test 2: Step reference validation ===")
    text = load("demo1.dsl")
    script = parse_text(text)

    for sid, step in script.steps.items():
        # Check branches
        for key, next_sid in step.branches.items():
            assert next_sid in script.steps, f"Undefined step {next_sid} in Branch of {sid}"

        # Silence
        if step.silence:
            assert step.silence in script.steps, f"Undefined silence {step.silence} in {sid}"

        # Default
        if step.default:
            assert step.default in script.steps, f"Undefined default {step.default} in {sid}"

    print("PASS: All references exist.")


# === Test 3: invalid keyword should raise an error ===
def test_invalid_keyword():
    print("\n=== Test 3: Invalid keyword detection ===")
    bad_script = """
    Step A
    Speek "hhh"
    """

    try:
        parse_text(bad_script)
        raise AssertionError("FAIL: invalid keyword should raise ParseError")
    except ParseError:
        print("PASS: Invalid keyword correctly detected.")


# === Test 4: missing Step name ===
def test_missing_step_name():
    print("\n=== Test 4: Missing Step name ===")
    bad_script = "Step\nSpeak \"hi\""

    try:
        parse_text(bad_script)
        raise AssertionError("FAIL: missing Step name should raise ParseError")
    except ParseError:
        print("PASS: Missing Step name correctly detected.")


# === Test 5: test expression parsing (variables + strings) ===
def test_expression_parsing():
    print("\n=== Test 5: Expression parsing ===")

    script = parse_text("""
        Step test
        Speak $user + "你好" + "世界"
    """)

    expr = script.steps["test"].speak
    assert expr.items[0].is_var and expr.items[0].value == "user"
    assert not expr.items[1].is_var and expr.items[1].value == "你好"
    assert not expr.items[2].is_var and expr.items[2].value == "世界"

    print("PASS: Expression parsing works.")


# === Test 6: test Listen parse ===
def test_listen_parse():
    print("\n=== Test 6: Listen parsing ===")

    script = parse_text("""
        Step t
        Listen 5, 20
    """)

    listen = script.steps["t"].listen
    assert listen.begin == 5
    assert listen.end == 20

    print("PASS: Listen parsing works.")


# === Test 7: test Exit parsing ===
def test_exit_parse():
    print("\n=== Test 7: Exit parsing ===")

    script = parse_text("""
        Step end
        Exit
    """)

    assert script.steps["end"].is_exit is True
    print("PASS: Exit parsing works.")


# === Test 8: test Branch parsing ===
def test_branch_parse():
    print("\n=== Test 8: Branch parsing ===")

    script = parse_text("""
        Step a
        Branch "投诉", next
        Step next
    """)

    assert script.steps["a"].branches["投诉"] == "next"
    print("PASS: Branch parsing works.")


# === Main test runner ===
if __name__ == "__main__":
    print("=== Running DSL Parser Tests ===")

    test_valid_file()
    test_references()
    test_invalid_keyword()
    test_missing_step_name()
    test_expression_parsing()
    test_listen_parse()
    test_exit_parse()
    test_branch_parse()

    print("\nAll tests completed.")
