import sys
import types


stub_novaprinter = types.ModuleType("novaprinter")


def _unexpected_pretty_printer(_result):
    raise AssertionError("prettyPrinter should be monkeypatched by the test that uses it")


stub_novaprinter.prettyPrinter = _unexpected_pretty_printer
sys.modules.setdefault("novaprinter", stub_novaprinter)