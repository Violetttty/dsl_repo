import shlex
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


# === AST node classes ===
@dataclass
class ExpressionItem:
    # Either variable or string literal
    is_var: bool
    value: str
    def __repr__(self):
        return f"${self.value}" if self.is_var else f"\"{self.value}\""

@dataclass
class Expression:
    items: List[ExpressionItem] = field(default_factory=list)
    def __repr__(self):
        return " + ".join(repr(i) for i in self.items)

@dataclass
class Listen:
    begin: int
    end: int
    def __repr__(self):
        return f"Listen({self.begin}, {self.end})"

@dataclass
class Step:
    step_id: str
    speak: Optional[Expression] = None
    listen: Optional[Listen] = None
    branches: Dict[str, str] = field(default_factory=dict)
    silence: Optional[str] = None
    default: Optional[str] = None
    is_exit: bool = False
    def __repr__(self):
        parts = [f"Step {self.step_id}:"]
        if self.speak: parts.append(f"  Speak: {self.speak}")
        if self.listen: parts.append(f"  {self.listen}")
        if self.branches: parts.append(f"  Branches: {self.branches}")
        if self.silence: parts.append(f"  Silence -> {self.silence}")
        if self.default: parts.append(f"  Default -> {self.default}")
        if self.is_exit: parts.append("  Exit")
        return "\n".join(parts)

@dataclass
class Script:
    steps: Dict[str, Step] = field(default_factory=dict)
    vars: Set[str] = field(default_factory=set)
    entry: Optional[str] = None
    def __repr__(self):
        items = [f"Script entry: {self.entry}"]
        for step in self.steps.values():
            items.append(repr(step))
        return "\n\n".join(items)


# === Helpers ===
def tidy_token(tok: str) -> str:
    return tok.rstrip(',')

def parse_expression(tokens: List[str], script_vars: Set[str]) -> Expression:
    expr = Expression()
    for tok in tokens:
        if tok == '+':
            continue
        if tok.startswith('$'):
            varname = tok[1:]
            script_vars.add(varname)
            expr.items.append(ExpressionItem(True, varname))
        else:
            expr.items.append(ExpressionItem(False, tok))
    return expr


# === Parser ===
class ParseError(Exception):
    pass


def parse_text(text: str) -> Script:
    script = Script()
    current_step = None
    lines = text.splitlines()

    for line_no, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue

        try:
            tokens = shlex.split(line, posix=True)
        except ValueError as e:
            raise ParseError(f"Line {line_no}: tokenization error: {e}")

        if not tokens:
            continue

        head = tokens[0]

        # ---- Step ----
        if head == "Step":
            if len(tokens) < 2:
                raise ParseError(f"Line {line_no}: Step missing id")
            step_id = tokens[1]
            if step_id in script.steps:
                raise ParseError(f"Line {line_no}: duplicate Step id '{step_id}'")
            current_step = Step(step_id)
            script.steps[step_id] = current_step
            if script.entry is None:
                script.entry = step_id

        # ---- Speak ----
        elif head == "Speak":
            if current_step is None:
                raise ParseError(f"Line {line_no}: Speak outside Step")
            expr_tokens = [tidy_token(t) for t in tokens[1:]]
            current_step.speak = parse_expression(expr_tokens, script.vars)

        # ---- Listen ----
        elif head == "Listen":
            if len(tokens) < 3:
                raise ParseError(f"Line {line_no}: Listen needs two integers")
            b = int(tidy_token(tokens[1]))
            e = int(tidy_token(tokens[2]))
            current_step.listen = Listen(b, e)

        # ---- Branch ----
        elif head == "Branch":
            if len(tokens) < 3:
                raise ParseError(f"Line {line_no}: Branch missing args")
            answer = tidy_token(tokens[1])
            next_step = tidy_token(tokens[2])
            current_step.branches[answer] = next_step

        # ---- Silence ----
        elif head == "Silence":
            current_step.silence = tokens[1]

        # ---- Default ----
        elif head == "Default":
            current_step.default = tokens[1]

        # ---- Exit ----
        elif head == "Exit":
            current_step.is_exit = True

        else:
            raise ParseError(f"Line {line_no}: unknown keyword '{head}'")

    # ---- Validate references ----
    for step in script.steps.values():
        refs = list(step.branches.values())
        if step.silence: refs.append(step.silence)
        if step.default: refs.append(step.default)
        for r in refs:
            if r not in script.steps:
                raise ParseError(f"Undefined step reference '{r}'")

    return script


# === Debug print helper ===
def pretty_print_script(script: Script):
    print(f"Script entry: {script.entry}")
    for sid, step in script.steps.items():
        print("-" * 40)
        print(step)
