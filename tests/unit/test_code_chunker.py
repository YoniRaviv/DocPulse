from docpulse.indexing.code_chunker import chunk_source

PY = """\
def helper(x):
    return x * 2


class AuthService:
    def login(self, user):
        return helper(user)
"""


def test_python_chunks():
    chunks = chunk_source("src/auth.py", PY)
    by_id = {c.id: c for c in chunks}
    assert "src/auth.py::helper" in by_id
    assert "src/auth.py::AuthService" in by_id
    assert "src/auth.py::AuthService.login" in by_id
    login = by_id["src/auth.py::AuthService.login"]
    assert login.kind == "method"
    assert login.signature == "def login(self, user):"
    assert login.start_line == 6
    assert by_id["src/auth.py::helper"].kind == "function"


def test_unknown_extension_returns_empty():
    assert chunk_source("notes.txt", "hello") == []


def test_nested_function_is_not_a_method():
    src = "def outer():\n    def inner():\n        pass\n    return inner\n"
    by_id = {c.id: c for c in chunk_source("src/n.py", src)}
    assert by_id["src/n.py::outer.inner"].kind == "function"


def test_decorated_method_includes_decorator():
    src = (
        "class C:\n"
        "    @classmethod\n"
        "    def create(cls):\n"
        "        pass\n"
    )
    by_id = {c.id: c for c in chunk_source("src/d.py", src)}
    create = by_id["src/d.py::C.create"]
    assert create.content.startswith("@classmethod")
    assert create.start_line == 2
    assert create.signature == "def create(cls):"
    assert create.kind == "method"


TS = """\
export function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export class CartService {
  addItem(sku: string): void {}
}

export interface CartItem {
  sku: string;
}
"""

CS = """\
namespace Shop {
    public interface IPricer {
        decimal Price(string sku);
    }

    public class Cart {
        public void AddItem(string sku) {}
    }
}
"""


def test_typescript_chunks():
    by_id = {c.id: c for c in chunk_source("src/cart.ts", TS)}
    assert by_id["src/cart.ts::formatPrice"].kind == "function"
    assert by_id["src/cart.ts::CartService.addItem"].kind == "method"
    assert by_id["src/cart.ts::CartItem"].kind == "interface"


def test_csharp_chunks():
    by_id = {c.id: c for c in chunk_source("src/Cart.cs", CS)}
    assert by_id["src/Cart.cs::IPricer"].kind == "interface"
    assert by_id["src/Cart.cs::Cart.AddItem"].kind == "method"
    assert by_id["src/Cart.cs::Cart"].kind == "class"
