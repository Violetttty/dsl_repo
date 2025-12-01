# dsl_parser.py
import shlex
import logging
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


# -------------------------
# Setup Parser Logger (独立文件 logs/parser.log)
# -------------------------
def setup_parser_logger():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "parser.log")

    logger = logging.getLogger("Parser")
    logger.setLevel(logging.INFO)

    # 单独文件输出
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)

    # 避免重复添加 handler
    if not logger.handlers:
        logger.addHandler(fh)

    return logger


parser_logger = setup_parser_logger()


# === AST Classes ===
@dataclass
class ExpressionItem:
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
        if self.speak:
            parts.append(f"  Speak: {self.speak}")
        if self.listen:
            parts.append(f"  {self.listen}")
        if self.branches:
            parts.append(f"  Branches: {self.branches}")
        if self.silence:
            parts.append(f"  Silence -> {self.silence}")
        if self.default:
            parts.append(f"  Default -> {self.default}")
        if self.is_exit:
            parts.append("  Exit")
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
    parser_logger.info(f"[Expression] Parsing tokens={tokens}")

    expr = Expression()
    for tok in tokens:
        if tok == '+':
            continue

        if tok.startswith('$'):
            varname = tok[1:]
            script_vars.add(varname)
            expr.items.append(ExpressionItem(True, varname))
            parser_logger.info(f"[Expression] Found variable: {varname}")
        else:
            expr.items.append(ExpressionItem(False, tok))
            parser_logger.info(f"[Expression] Found literal: {tok}")

    return expr


# === Parser core ===
class ParseError(Exception):
    pass


def parse_text(text: str) -> Script:
    parser_logger.info("========== Parser Start ==========")

    script = Script()
    current_step = None
    lines = text.splitlines()

    for line_no, raw in enumerate(lines, 1):
        line = raw.strip()

        # Skip empty lines
        if not line:
            continue
        # Skip comments
        if line.startswith("#"):
            parser_logger.info(f"[Line {line_no}] Comment skipped.")
            continue

        parser_logger.info(f"[Line {line_no}] Raw: {line}")

        try:
            tokens = shlex.split(line, posix=True)
        except ValueError as e:
            parser_logger.error(f"[Line {line_no}] tokenization error: {e}")
            raise ParseError(f"Line {line_no}: tokenization error: {e}")

        if not tokens:
            continue

        head = tokens[0]
        parser_logger.info(f"[Line {line_no}] Head token → {head}")

        # ---- Step ----
        if head == "Step":
            if len(tokens) < 2:
                raise ParseError(f"Line {line_no}: Step missing id")

            step_id = tokens[1]
            parser_logger.info(f"[Step] New step '{step_id}'")

            if step_id in script.steps:
                parser_logger.error(f"[Error] Duplicate Step id '{step_id}'")
                raise ParseError(f"Line {line_no}: duplicate Step id '{step_id}'")

            current_step = Step(step_id)
            script.steps[step_id] = current_step

            if script.entry is None:
                script.entry = step_id
                parser_logger.info(f"[Entry] Set entry step → {step_id}")

        # ---- Speak ----
        elif head == "Speak":
            if current_step is None:
                raise ParseError(f"Line {line_no}: Speak outside Step")

            expr_tokens = [tidy_token(t) for t in tokens[1:]]
            parser_logger.info(f"[Speak] Tokens: {expr_tokens}")

            current_step.speak = parse_expression(expr_tokens, script.vars)

        # ---- Listen ----
        elif head == "Listen":
            if len(tokens) < 3:
                raise ParseError(f"Line {line_no}: Listen needs two integers")

            b = int(tidy_token(tokens[1]))
            e = int(tidy_token(tokens[2]))
            current_step.listen = Listen(b, e)

            parser_logger.info(f"[Listen] Listen({b},{e}) in step {current_step.step_id}")

        # ---- Branch ----
        elif head == "Branch":
            if len(tokens) < 3:
                raise ParseError(f"Line {line_no}: Branch missing args")

            answer = tidy_token(tokens[1])
            next_step = tidy_token(tokens[2])

            current_step.branches[answer] = next_step
            parser_logger.info(f"[Branch] '{answer}' -> {next_step}")

        # ---- Silence ----
        elif head == "Silence":
            target = tokens[1]
            current_step.silence = target
            parser_logger.info(f"[Silence] -> {target}")

        # ---- Default ----
        elif head == "Default":
            target = tokens[1]
            current_step.default = target
            parser_logger.info(f"[Default] -> {target}")

        # ---- Exit ----
        elif head == "Exit":
            current_step.is_exit = True
            parser_logger.info("[Exit] Marked as exit step.")

        else:
            parser_logger.error(f"[Error] Unknown keyword '{head}' at line {line_no}")
            raise ParseError(f"Line {line_no}: unknown keyword '{head}'")

    # ---- Validate references ----
    parser_logger.info("[Validation] Checking references...")

    for step in script.steps.values():
        refs = list(step.branches.values())
        if step.silence:
            refs.append(step.silence)
        if step.default:
            refs.append(step.default)

        for r in refs:
            if r not in script.steps:
                parser_logger.error(f"[Error] Undefined step reference '{r}'")
                raise ParseError(f"Undefined step reference '{r}'")

    parser_logger.info("========== Parser Success ==========")
    return script
