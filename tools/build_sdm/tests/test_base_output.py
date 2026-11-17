import pytest
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ValidationError, StrictStr

from base_output import OutputPlugin  # Adjust if module path differs


def _reset_registry_cycle():
    '''
    Generator implementing the snapshot/clear/restore cycle used by the
    `reset_registry` fixture below.

    This is extracted into a plain function (rather than living directly in
    the fixture body) so `test_reset_registry_restores_prior_registrations`
    can drive it directly via `next()` and inspect the registry at each
    phase boundary. Pytest fixture functions refuse to be called directly,
    so the fixture itself can't be exercised that way -- it just delegates
    to this generator via `yield from`.
    '''
    original = OutputPlugin.registry.copy()
    OutputPlugin.registry.clear()
    yield
    OutputPlugin.registry.clear()
    OutputPlugin.registry.update(original)


@pytest.fixture(autouse=True)
def reset_registry():
    '''
    Automatically clear the OutputPlugin registry before each test, then
    restore whatever was registered beforehand once the test completes.

    This ensures that tests remain isolated and do not leak plugin
    definitions into one another. Without the snapshot/restore, the registry
    would be left permanently empty after this module's tests finish,
    breaking any test file that runs later in the session and relies on
    real plugins (e.g. output_plugins.*) having been registered at import
    time.
    '''
    yield from _reset_registry_cycle()


def test_output_plugin_instantiation_fails():
    '''
    Verify that OutputPlugin cannot be instantiated directly.

    Since OutputPlugin declares abstract methods, Python should raise
    a TypeError when attempting to instantiate it directly.
    '''
    with pytest.raises(TypeError):
        _ = OutputPlugin()


class DummyPlugin(OutputPlugin):
    '''
    Minimal concrete plugin used for testing base functionality.
    '''
    def generate(self, gim_config: dict, output_dir: Path, plugin_config: Optional[dict] = None) -> None:
        pass


class DummyConfig(BaseModel):
    '''
    Example Pydantic schema used for configuration validation tests.
    '''
    field: StrictStr = Field(..., description='Required string field')


def test_registry_registers_concrete_plugin():
    '''
    Confirm that defining a concrete subclass of OutputPlugin adds it to the registry.

    The registry should contain the fully qualified class name as the key,
    and the subclass itself as the value.
    '''
    class ConcretePlugin(OutputPlugin):
        def generate(self, gim_config, output_dir, plugin_config=None):
            return 'ok'

    fq_key = f'{ConcretePlugin.__module__}.{ConcretePlugin.__qualname__}'
    assert fq_key in OutputPlugin.registry
    assert OutputPlugin.registry[fq_key] is ConcretePlugin


def test_reset_registry_restores_prior_registrations():
    '''
    Regression test for the reset_registry fixture's snapshot/restore cycle.

    Plugins registered before a reset/restore cycle starts (e.g. real
    plugins imported earlier in the pytest session, before this module's
    tests ever ran) must still be present once the cycle's teardown phase
    completes, while anything registered *during* the cycle (simulating a
    test body) must not leak forward into whatever runs next.

    This drives `_reset_registry_cycle` directly, the same generator the
    `reset_registry` fixture delegates to, rather than going through pytest's
    fixture machinery (which refuses to be called like a normal function).
    If `_reset_registry_cycle` regressed back to a clear-only implementation
    with no snapshot/restore, `pre_existing_key` would be missing from the
    registry after the cycle completes and this test would fail.
    '''
    class PreExistingPlugin(OutputPlugin):
        def generate(self, gim_config, output_dir, plugin_config=None):
            pass

    pre_existing_key = f'{PreExistingPlugin.__module__}.{PreExistingPlugin.__qualname__}'
    assert pre_existing_key in OutputPlugin.registry

    cycle = _reset_registry_cycle()
    next(cycle)  # setup phase: snapshot the registry, then clear it
    assert OutputPlugin.registry == {}

    class ThrowawayDuringCycle(OutputPlugin):
        def generate(self, gim_config, output_dir, plugin_config=None):
            pass

    with pytest.raises(StopIteration):
        next(cycle)  # teardown phase: clear, then restore the snapshot

    assert pre_existing_key in OutputPlugin.registry
    assert not any('ThrowawayDuringCycle' in key for key in OutputPlugin.registry)


def test_registry_excludes_abstract_plugins():
    '''
    Ensure abstract subclasses are not registered.

    Subclasses that fail to implement abstract methods should be excluded
    from the registry by the `inspect.isabstract` filter.
    '''
    class AbstractPlugin(OutputPlugin):
        pass  # no implementation of `generate`

    fq_names = set(OutputPlugin.registry.keys())
    assert not any('AbstractPlugin' in key for key in fq_names)


def test_logger_is_initialized():
    '''
    Verify that plugin instances have a properly initialized logger.

    The logger should be a `logging.Logger` with a name of the form
    'plugin.<ClassName>'.
    '''
    plugin = DummyPlugin()
    assert isinstance(plugin.logger, logging.Logger)
    assert plugin.logger.name == f'plugin.{plugin.__class__.__name__}'


def test_load_plugin_config_none():
    '''
    If no config_schema is defined, load_plugin_config should return None.

    This ensures plugins without schema requirements can safely ignore
    configuration dictionaries.
    '''
    class NoSchemaPlugin(OutputPlugin):
        def generate(self, gim_config: dict, output_dir: Path, plugin_config: Optional[dict] = None) -> None:
            pass

    assert NoSchemaPlugin.load_plugin_config({'any': 'data'}) is None


def test_load_plugin_config_valid():
    '''
    Validate that load_plugin_config returns a Pydantic model instance
    when a schema is defined and input is valid.
    '''
    class WithSchemaPlugin(DummyPlugin):
        config_schema = DummyConfig

    config = WithSchemaPlugin.load_plugin_config({'field': 'value'})
    assert isinstance(config, DummyConfig)
    assert config.field == 'value'


def test_load_plugin_config_invalid():
    '''
    Validate that load_plugin_config raises ValidationError on invalid input.

    This ensures plugins enforce their Pydantic schemas at runtime.
    '''
    class WithSchemaPlugin(DummyPlugin):
        config_schema = DummyConfig

    with pytest.raises(ValidationError):
        _ = WithSchemaPlugin.load_plugin_config({'field': 123})  # wrong type


def test_registry_distinguishes_same_classname_in_different_scopes():
    '''
    Ensure registry keys are fully qualified and prevent collisions
    between classes with the same simple name in different scopes.
    '''

    def factory():
        class DuplicateNamePlugin(OutputPlugin):
            def generate(self, gim_config: dict, output_dir: Path, plugin_config: Optional[dict] = None):
                pass
        return DuplicateNamePlugin

    p1 = factory()
    p2 = factory()

    fq_names = set(OutputPlugin.registry.keys())
    assert any(p1.__qualname__ in k for k in fq_names)
    assert any(p2.__qualname__ in k for k in fq_names)
    # Each class should have a unique entry despite sharing a simple name
