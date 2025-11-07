import tkinter as tk
from tkinter import ttk
import ast
import operator

# ---------- Safe expression evaluator (no eval) ----------
# Supports: +, -, *, /, //, %, **, unary +/-, parentheses, integers & decimals

_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

def _eval_ast(node):
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)

    # Numbers (int/float)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    # Handle older Python versions that use Num
    if hasattr(ast, "Num") and isinstance(node, ast.Num):
        return node.n

    # Unary operations (+x, -x)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
        return _ALLOWED_UNARY_OPS[type(node.op)](_eval_ast(node.operand))

    # Binary operations (x+y, x-y, x*y, etc.)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        op_func = _ALLOWED_BIN_OPS[type(node.op)]
        # Protect against division by zero and overly large exponents
        if op_func in (operator.truediv, operator.floordiv, operator.mod) and right == 0:
            raise ZeroDivisionError("division by zero")
        if op_func is operator.pow and abs(right) > 1000:
            raise ValueError("exponent too large")
        return op_func(left, right)

    # Parentheses are represented by nested nodes; nothing special to do.

    raise ValueError("Invalid expression")

def safe_eval(expr: str):
    # Convert unicode division symbols etc. if pasted
    expr = expr.replace("×", "*").replace("÷", "/")
    # Allow decimals like ".5" by prefixing 0 when needed (visual only)
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError("Syntax error") from e
    return _eval_ast(tree)

# ---------- GUI Calculator ----------
class Calculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calculator")
        self.resizable(False, False)

        self.expression = tk.StringVar(value="")
        self.result = tk.StringVar(value="0")

        self._build_ui()
        self._bind_keys()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.grid(sticky="nsew")

        # Display: expression and result
        expr_entry = ttk.Entry(outer, textvariable=self.expression, font=("Consolas", 16))
        expr_entry.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 6))
        expr_entry.focus()

        result_lbl = ttk.Label(outer, textvariable=self.result, anchor="e", font=("Consolas", 20))
        result_lbl.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        # Buttons (row, col, text, command)
        buttons = [
            ("C",  2, 0, self.clear),
            ("⌫",  2, 1, self.backspace),
            ("(",  2, 2, lambda: self.insert("(")),
            (")",  2, 3, lambda: self.insert(")")),

            ("7",  3, 0, lambda: self.insert("7")),
            ("8",  3, 1, lambda: self.insert("8")),
            ("9",  3, 2, lambda: self.insert("9")),
            ("÷",  3, 3, lambda: self.insert("/")),

            ("4",  4, 0, lambda: self.insert("4")),
            ("5",  4, 1, lambda: self.insert("5")),
            ("6",  4, 2, lambda: self.insert("6")),
            ("×",  4, 3, lambda: self.insert("*")),

            ("1",  5, 0, lambda: self.insert("1")),
            ("2",  5, 1, lambda: self.insert("2")),
            ("3",  5, 2, lambda: self.insert("3")),
            ("−",  5, 3, lambda: self.insert("-")),

            ("0",  6, 0, lambda: self.insert("0")),
            (".",  6, 1, lambda: self.insert(".")),
            ("%",  6, 2, lambda: self.insert("%")),
            ("+",  6, 3, lambda: self.insert("+")),

            ("//", 7, 0, lambda: self.insert("//")),
            ("^",  7, 1, lambda: self.insert("**")),  # caret shows as power
            ("=",  7, 2, self.calculate),
        ]

        for (text, r, c, cmd) in buttons:
            style = "TButton"
            btn = ttk.Button(outer, text=text, command=cmd, style=style)
            # Make the "=" button span two columns for emphasis
            if text == "=":
                btn.grid(row=r, column=c, columnspan=2, sticky="nsew", padx=2, pady=2, ipadx=10, ipady=10)
            else:
                btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2, ipadx=10, ipady=10)

        # Grid weights for uniform sizing
        for i in range(4):
            outer.grid_columnconfigure(i, weight=1)
        for i in range(8):
            outer.grid_rowconfigure(i, weight=1)

    def _bind_keys(self):
        # Digits & operators
        for ch in "0123456789.+-*/()%":
            self.bind(ch, lambda e, s=ch: self.insert(s))
        # Extra keys
        self.bind("<Return>", lambda e: self.calculate())
        self.bind("=",        lambda e: self.calculate())
        self.bind("<KP_Enter>", lambda e: self.calculate())
        self.bind("<BackSpace>", lambda e: self.backspace())
        self.bind("<Delete>", lambda e: self.clear())
        # Power via caret
        self.bind("^", lambda e: self.insert("**"))

    def insert(self, s: str):
        # Append token to expression
        self.expression.set(self.expression.get() + s)

    def backspace(self):
        expr = self.expression.get()
        # Handle backspace for '**' as one caret
        if expr.endswith("**"):
            self.expression.set(expr[:-2])
        else:
            self.expression.set(expr[:-1] if expr else "")

    def clear(self):
        self.expression.set("")
        self.result.set("0")

    def calculate(self):
        expr = self.expression.get().strip()
        if not expr:
            self.result.set("0")
            return
        try:
            value = safe_eval(expr)
            # Display integers without .0
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            self.result.set(str(value))
        except ZeroDivisionError:
            self.result.set("Error: ÷ by 0")
        except Exception:
            self.result.set("Error")
        # Keep expression so users can edit; alternatively uncomment next line:
        # self.expression.set(str(self.result.get()))

if __name__ == "__main__":
    # Use a default ttk theme for a clean look
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # crisp on Windows
    except Exception:
        pass
    app = Calculator()
    app.mainloop()
