from langchain.tools import tool
import ast, operator

_ALLOWED = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Num):  
        return node.n
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError("지원하지 않는 표현식입니다.")

@tool
def calculator(expression: str) -> float:
    """숫자 + 사칙연산 + 제곱(**)이 포함된 수식을 계산합니다."""
    try:
        tree = ast.parse(expression, mode="eval")
        return _eval(tree.body)
    except Exception:
        return "잘못된 수식입니다."