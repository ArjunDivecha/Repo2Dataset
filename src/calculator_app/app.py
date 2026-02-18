"""
Flask Calculator Application

A robust web-based calculator with support for basic operations:
- Addition, subtraction, multiplication, division
- Input validation and error handling
- Keyboard support
- Clean, responsive UI
"""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


class Calculator:
    """Calculator class managing state and operations."""

    def __init__(self):
        """Initialize calculator with default state."""
        self.reset()

    def reset(self):
        """Reset calculator to initial state."""
        self.current_input = "0"
        self.stored_value = None
        self.pending_op = None
        self.last_action = clear
        self.error = None
        self.display_expression = ""

    def input_digit(self, digit: str):
        """
        Add a digit to current input.

        Args:
            digit: Single digit character (0-9)
        """
        if self.error:
            self.reset()

        if self.current_input == "0" or self.last_action == "equals" or self.last_action == "op":
            self.current_input = digit
        else:
            if len(self.current_input.replace("-", "").replace(".", "")) < 15:
                self.current_input += digit

        self.last_action = "digit"

    def input_dot(self):
        """Add decimal point to current input."""
        if self.error:
            self.reset()

        if "." not in self.current_input:
            if self.last_action == "equals" or self.last_action == "op":
                self.current_input = "0."
            else:
                self.current_input += "."

        self.last_action = "digit"

    def set_operation(self, op: str):
        """
        Set the pending operation.

        Args:
            op: One of '+', '-', '*', '/'
        """
        if self.error:
            self.reset()

        if self.stored_value is not None and self.pending_op and self.last_action != "op":
            # Perform the previous operation first
            self.compute()

        op_symbol = self._get_op_symbol(op)
        self.display_expression = f"{self._format_number(float(self.current_input))} {op_symbol}"
        self.stored_value = float(self.current_input)
        self.current_input = "0"
        self.pending_op = op
        self.last_action = "op"

    def compute(self):
        """Perform the pending operation and store result in current_input."""
        if self.error:
            self.reset()
            return

        if self.stored_value is None or self.pending_op is None:
            return

        try:
            current = float(self.current_input)
            result = self._perform_operation(self.stored_value, current, self.pending_op)

            # Check for overflow
            if abs(result) > 1e100:
                raise OverflowError("Result too large")

            # Format result
            if result.is_integer():
                self.current_input = str(int(result))
            else:
                # Round to avoid floating point issues
                self.current_input = f"{result:.10g}".rstrip("0").rstrip(".")

            op_symbol = self._get_op_symbol(self.pending_op)
            self.display_expression = (
                f"{self._format_number(self.stored_value)} {op_symbol} {self._format_number(current)} ="
            )
            self.stored_value = None
            self.pending_op = None
            self.last_action = "equals"

        except ZeroDivisionError:
            self.error = "Cannot divide by zero"
            self.current_input = "Error"
        except OverflowError as e:
            self.error = str(e)
            self.current_input = "Error"
        except Exception as e:
            self.error = "Calculation error"
            self.current_input = "Error"

    def backspace(self):
        """Remove the last digit from current input."""
        if self.error:
            self.reset()

        if self.last_action == "equals":
            self.reset()
            return

        if self.last_action == "op":
            # Don't backspace if we just pressed an operator
            return

        if len(self.current_input) > 1:
            self.current_input = self.current_input[:-1]
        else:
            self.current_input = "0"

        self.last_action = "digit"

    def toggle_sign(self):
        """Toggle between positive and negative."""
        if self.error:
            self.reset()

        if self.current_input != "0":
            if self.current_input.startswith("-"):
                self.current_input = self.current_input[1:]
            else:
                if len(self.current_input) < 15:
                    self.current_input = "-" + self.current_input

        self.last_action = "digit"

    def percentage(self):
        """Convert current value to percentage."""
        if self.error:
            self.reset()

        try:
            value = float(self.current_input)
            result = value / 100

            if result.is_integer():
                self.current_input = str(int(result))
            else:
                self.current_input = f"{result:.10g}".rstrip("0").rstrip(".")

            self.last_action = "digit"
        except Exception:
            pass

    @staticmethod
    def _perform_operation(a: float, b: float, op: str) -> float:
        """
        Perform a single arithmetic operation.

        Args:
            a: First operand
            b: Second operand
            op: Operation to perform ('+', '-', '*', '/')

        Returns:
            Result of the operation

        Raises:
            ZeroDivisionError: If division by zero
        """
        operations = {
            "+": lambda x, y: x + y,
            "-": lambda x, y: x - y,
            "*": lambda x, y: x * y,
            "/": lambda x, y: x / y if y != 0 else (_ for _ in ()).throw(ZeroDivisionError()),
        }

        return operations[op](a, b)

    @staticmethod
    def _get_op_symbol(op: str) -> str:
        """Convert internal op symbol to display symbol."""
        symbols = {"+": "+", "-": "−", "*": "×", "/": "÷"}
        return symbols.get(op, op)

    @staticmethod
    def _format_number(num: float) -> str:
        """Format number for display."""
        if num.is_integer():
            return str(int(num))
        else:
            return f"{num:.10g}".rstrip("0").rstrip(".")


# Global calculator instance
calculator = Calculator()


@app.route("/")
def index():
    """Render the main calculator page."""
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """
    Handle calculator operations via API.

    Expected JSON payload:
        {
            "action": "digit|dot|op|equals|clear|backspace|toggle_sign|percentage",
            "value": "..."  // depends on action
        }

    Returns:
        JSON response with current calculator state
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    action = data.get("action", "")

    if action == "digit":
        digit = data.get("value")
        if digit and digit.isdigit() and len(digit) == 1:
            calculator.input_digit(digit)
    elif action == "dot":
        calculator.input_dot()
    elif action == "op":
        op = data.get("value")
        if op in ["+", "-", "*", "/"]:
            calculator.set_operation(op)
    elif action == "equals":
        calculator.compute()
    elif action == "clear":
        calculator.reset()
    elif action == "backspace":
        calculator.backspace()
    elif action == "toggle_sign":
        calculator.toggle_sign()
    elif action == "percentage":
        calculator.percentage()
    else:
        return jsonify({"error": f"Unknown action: {action}"}), 400

    return jsonify(
        {
            "current_input": calculator.current_input,
            "display_expression": calculator.display_expression,
            "error": calculator.error,
        }
    )


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset calculator to initial state."""
    calculator.reset()
    return jsonify(
        {"current_input": "0", "display_expression": "", "error": None}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)