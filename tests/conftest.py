import asyncio
import time
import pytest

from circuitbreaker import CircuitBreaker, CircuitBreakerMonitor


def _function_factory(is_async, is_generator, inner_call):
    if is_async:
        if is_generator:
            async def _function(*a, **kwa):
                yield inner_call(*a, **kwa)
        else:
            async def _function(*a, **kwa):
                return inner_call(*a, **kwa)
    else:
        if is_generator:
            def _function(*a, **kwa):
                yield inner_call(*a, **kwa)
        else:
            def _function(*a, **kwa):
                return inner_call(*a, **kwa)
    return _function


@pytest.fixture(autouse=True)
def clean_circuit_breaker_monitor():
    CircuitBreakerMonitor.circuit_breakers = {}


@pytest.fixture(params=[True, False], ids=["async", "sync"])
def is_async(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["generator", "function"])
def is_generator(request):
    return request.param


@pytest.fixture
def resolve_call(is_async, is_generator):
    """
    This fixture helps abstract calls from other fixtures that have sync and
    async, function and generator versions.

    For example, this:
        if is_async:
            if is_generator:
                result = [el async for el in function()]
            else:
                result = await function()
        else:
            if is_generator:
                result = list(function())
            else:
                result = function()

    Can be replaced with:
        result = await resolve_call(function())

    """
    async def _sync(value):
        return value

    async def _sync_gen(generator):
        return list(generator)

    async def _async(coroutine):
        return await coroutine

    async def _async_gen(async_generator):
        return [el async for el in async_generator]

    async_, sync_, generator_, function_ = (True, False) * 2

    dispatch = {
        (sync_, function_): _sync,
        (sync_, generator_): _sync_gen,
        (async_, function_): _async,
        (async_, generator_): _async_gen,
    }
    return dispatch[is_async, is_generator]


@pytest.fixture
def sleep(is_async):
    async def _sleep(secs):
        if is_async:
            await asyncio.sleep(secs)
        else:
            time.sleep(secs)

    return _sleep


@pytest.fixture
def mock_function_call(mocker):
    return mocker.Mock(return_value=object())


@pytest.fixture
def mock_fallback_call(mocker):
    return mocker.Mock(return_value=object())


@pytest.fixture
def function_call_return_value(is_generator, mock_function_call):
    value = mock_function_call.return_value
    return [value] if is_generator else value


@pytest.fixture
def fallback_call_return_value(is_generator, mock_fallback_call):
    value = mock_fallback_call.return_value
    return [value] if is_generator else value


@pytest.fixture
def function_call_error(mock_function_call):
    error = IOError
    mock_function_call.side_effect = error
    return error


@pytest.fixture
def function(is_async, is_generator, mock_function_call):
    return _function_factory(is_async, is_generator, mock_function_call)


@pytest.fixture
def fallback_function(is_async, is_generator, mock_fallback_call):
    return _function_factory(is_async, is_generator, mock_fallback_call)


@pytest.fixture
def circuit_success(function):
    return CircuitBreaker()(function)


@pytest.fixture
def circuit_failure(function, function_call_error):
    return CircuitBreaker(
        failure_threshold=1,
        name="circuit_failure",
    )(function)


@pytest.fixture
def circuit_threshold_1(function):
    return CircuitBreaker(
        failure_threshold=1,
        name="threshold_1",
    )(function)


@pytest.fixture
def circuit_threshold_2_timeout_1(function):
    return CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=1,
        name="threshold_2",
    )(function)


@pytest.fixture
def circuit_threshold_3_timeout_1(function):
    return CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1,
        name="threshold_3",
    )(function)
