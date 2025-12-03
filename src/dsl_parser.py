# dsl_parser.py
import shlex
import logging
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


#############################################
#                Logging                   #
#############################################
def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("Parser")
    logger.setLevel(logging.INFO)

    log_file = os.path.join(log_dir, "parser.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(fh)

    return logger


logger = setup_logger()


#############################################
#                AST Nodes                 #
#############################################
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
    # 支持每个 Step 中有多条 Action 语句
    # 每个元素形如 {"name": str, "args": List[str]}
    actions: List[Dict[str, List[str]]] = field(default_factory=list)

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
        if self.actions:
            parts.append(f"  Actions: {[ (a['name'], a['args']) for a in self.actions ]}")
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


#############################################
#              Helper Functions             #
#############################################
def tidy_token(tok: str) -> str:
    return tok.rstrip(",")


def parse_expression(tokens: List[str], script_vars: Set[str]) -> Expression:
    expr = Expression()
    logger.info(f"[Parser] Parsing expression tokens: {tokens}")

    for tok in tokens:
        if tok == "+":
            continue

        if tok.startswith("$"):
            varname = tok[1:]
            script_vars.add(varname)
            expr.items.append(ExpressionItem(True, varname))
            logger.info(f"[Parser] Found variable: {varname}")
        else:
            expr.items.append(ExpressionItem(False, tok))
            logger.info(f"[Parser] Found literal: {tok}")

    return expr


#############################################
#                  Parser                   #
#############################################
class ParseError(Exception):
    pass


def parse_text(text: str) -> Script:
    logger.info("========== Parsing Started ==========")

    script = Script()
    current_step = None
    lines = text.splitlines()

    for line_no, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        try:
            tokens = shlex.split(line, posix=True)
        except Exception as e:
            raise ParseError(f"Line {line_no}: tokenization error: {e}")

        if not tokens:
            continue

        head = tokens[0]

        #############################################
        # Step
        #############################################
        if head == "Step":
            if len(tokens) < 2:
                raise ParseError(f"Line {line_no}: Step missing id")

            step_id = tokens[1]
            if step_id in script.steps:
                raise ParseError(f"Line {line_no}: duplicate Step id '{step_id}'")

            current_step = Step(step_id)
            script.steps[step_id] = current_step
            logger.info(f"[Parser] New Step: {step_id}")

            if script.entry is None:
                script.entry = step_id

        #############################################
        # Speak
        #############################################
        elif head == "Speak":
            expr_tokens = [tidy_token(t) for t in tokens[1:]]
            current_step.speak = parse_expression(expr_tokens, script.vars)
            logger.info(f"[Parser] Step {current_step.step_id}: Speak parsed")

        #############################################
        # Listen
        #############################################
        elif head == "Listen":
            b = int(tidy_token(tokens[1]))
            e = int(tidy_token(tokens[2]))
            current_step.listen = Listen(b, e)
            logger.info(f"[Parser] Step {current_step.step_id}: Listen({b},{e})")

        #############################################
        # Branch
        #############################################
        elif head == "Branch":
            answer = tidy_token(tokens[1])
            next_step = tidy_token(tokens[2])
            current_step.branches[answer] = next_step
            logger.info(f"[Parser] Step {current_step.step_id}: Branch {answer} -> {next_step}")

        #############################################
        # Silence
        #############################################
        elif head == "Silence":
            current_step.silence = tokens[1]
            logger.info(f"[Parser] Step {current_step.step_id}: Silence -> {tokens[1]}")

        #############################################
        # Default
        #############################################
        elif head == "Default":
            current_step.default = tokens[1]
            logger.info(f"[Parser] Step {current_step.step_id}: Default -> {tokens[1]}")

        #############################################
        # Action
        #############################################
        elif head == "Action":
            if current_step is None:
                raise ParseError(f"Line {line_no}: Action outside Step")

            if len(tokens) < 2:
                raise ParseError(f"Line {line_no}: Action missing name")

            # 支持一个 Step 中多条 Action
            name = tokens[1]
            args: List[str] = []
            if len(tokens) > 2:
                args = [tidy_token(t) for t in tokens[2:]]
                
            # 真正用于运行时的 Action 列表
            current_step.actions.append({"name": name, "args": args})

            # Logging
            logger.info(f"[Parser] Parsed Action {name}, args={args}")

        #############################################
        # Exit
        #############################################
        elif head == "Exit":
            current_step.is_exit = True
            logger.info(f"[Parser] Step {current_step.step_id}: Exit")

        else:
            raise ParseError(f"Line {line_no}: unknown keyword '{head}'")

    #############################################
    # Validate Step references
    #############################################
    for step in script.steps.values():
        refs = []

        refs += list(step.branches.values())
        if step.silence:
            refs.append(step.silence)
        if step.default:
            refs.append(step.default)

        for r in refs:
            if r not in script.steps:
                raise ParseError(f"Undefined step reference '{r}'")

    logger.info("========== Parsing Completed ==========")
    return script


#############################################
#            Pretty Print Helper            #
#############################################
def pretty_print_script(script: Script) -> None:
    """
    简单地打印 Script 结构，供测试和调试使用。
    test/test_parser.py 会从这里导入该函数。
    """
    print(repr(script))