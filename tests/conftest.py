import sys
import types


stub_novaprinter = types.ModuleType("novaprinter")


def _unexpected_pretty_printer(_result):
    raise AssertionError("prettyPrinter should be monkeypatched by the test that uses it")


stub_novaprinter.prettyPrinter = _unexpected_pretty_printer
sys.modules.setdefault("novaprinter", stub_novaprinter)


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run live Nova3 integration tests",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return

    live_items = [item for item in items if "live" in item.keywords]
    if not live_items:
        return

    config.hook.pytest_deselected(items=live_items)
    items[:] = [item for item in items if "live" not in item.keywords]
