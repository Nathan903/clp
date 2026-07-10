"""Functions for facilitating the port connections for the CLP package."""

import socket
from dataclasses import dataclass
from typing import Any

from clp_py_utils.clp_config import (
    ClpConfig,
    REDUCER_COMPONENT_NAME,
)

# Port constants.
MIN_NON_PRIVILEGED_PORT = 1024
MAX_PORT = 65535
VALID_PORT_RANGE = range(MIN_NON_PRIVILEGED_PORT, MAX_PORT + 1)

# Practical maximum number of reducer instances.
REDUCER_MAX_PORTS = 128

# Attribute names used to discover port configuration in component objects.
PORT_ATTR_NAMES = ["port", "base_port"]


@dataclass
class PortAssignment:
    """
    Represents a port assignment for a CLP component.

    :param component: The component configuration object that needs port assignment.
    :param attr_name: The name of the port attribute on the component.
    :param port_count: The number of consecutive ports needed by this component.
    """

    component: Any
    attr_name: str
    port_count: int


def assign_ports_from_base(base_port: int, clp_config: ClpConfig) -> None:
    """
    Assign ports to all components in `clp_config` that require them, starting from the first
    available range at or after `base_port`. Ports are assigned sequentially, with each component
    receiving the number of ports it requires.

    :param base_port:
    :param clp_config:
    :raise ValueError: If no large enough port range is available.
    """
    # Discover which components need port assignments.
    port_assignments = _discover_port_assignments(clp_config)
    total_ports_needed = sum(assignment.port_count for assignment in port_assignments)

    # Find the first range large enough to assign all required ports.
    port_range = _find_available_port_range(
        base_port=base_port,
        host="127.0.0.1",
        port_count=total_ports_needed,
    )

    # Assign ports to the components.
    current_port = port_range.start
    for assignment in port_assignments:
        setattr(assignment.component, assignment.attr_name, current_port)
        current_port += assignment.port_count


def _find_available_port_range(base_port: int, host: str, port_count: int) -> range:
    """
    Find the first contiguous range of available ports at or after `base_port`.

    :param base_port:
    :param host:
    :param port_count:
    :return: The available port range.
    :raise ValueError: If no large enough range is available.
    """
    if port_count <= 0:
        return range(base_port, base_port)

    candidate_base_port = base_port
    while candidate_base_port + port_count - 1 <= MAX_PORT:
        port_range = range(candidate_base_port, candidate_base_port + port_count)
        _validate_port_range_bounds(port_range)

        unavailable_port = _find_unavailable_port(host=host, port_range=port_range)
        if unavailable_port is None:
            return port_range

        candidate_base_port = unavailable_port + 1

    requested_range = range(base_port, base_port + port_count)
    err_msg = (
        f"No available range of {port_count} ports was found at or after "
        f"{_format_port_range(requested_range)}."
    )
    raise ValueError(err_msg)


def _find_unavailable_port(host: str, port_range: range) -> int | None:
    """
    Finds the first unavailable port in the given range.

    :param host:
    :param port_range:
    :return: The first unavailable port, or None if all ports are available.
    """
    for port in port_range:
        if not _is_port_free(port=port, host=host):
            return port
    return None


def _discover_port_assignments(clp_config: ClpConfig) -> list[PortAssignment]:
    """
    Discover which components in `clp_config` require port assignments.

    :param clp_config:
    :return: A list of PortAssignment objects describing what ports each component needs.
    """
    port_assignments: list[PortAssignment] = []

    for component_name, component_config in vars(clp_config).items():
        # Skip private attributes and None values.
        if component_name.startswith("_") or component_config is None:
            continue

        # Check if this component has a port attribute.
        port_attr_name = None
        for attr_name in PORT_ATTR_NAMES:
            if hasattr(component_config, attr_name):
                port_attr_name = attr_name
                break
        if port_attr_name is None:
            continue

        # Determine how many ports this component needs.
        port_count = REDUCER_MAX_PORTS if component_name == REDUCER_COMPONENT_NAME else 1

        port_assignments.append(
            PortAssignment(
                component=component_config,
                attr_name=port_attr_name,
                port_count=port_count,
            )
        )

    return port_assignments


def _format_port_range(port_range: range) -> str:
    """
    Format a port range as a human-readable string.

    :param port_range:
    :return: A string like "'1024' to '65535' inclusive".
    """
    start_port = port_range.start
    end_port = port_range.stop - 1
    return f"'{start_port}' to '{end_port}' inclusive"


def _is_port_free(port: int, host: str) -> bool:
    """
    Check whether a TCP port is available for binding.

    :param port:
    :param host:
    :return: True if the port can be bound, otherwise False.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
        return True


def _validate_port_range_bounds(port_range: range) -> None:
    """
    Validates that the given port range falls within the valid port range.

    :param port_range:
    :raise ValueError: If any part of the range falls outside valid port numbers.
    """
    start_port = port_range.start
    end_port = port_range.stop - 1
    min_valid_port = VALID_PORT_RANGE.start
    max_valid_port = VALID_PORT_RANGE.stop - 1

    if start_port < min_valid_port or end_port > max_valid_port:
        required_range_str = _format_port_range(port_range)
        valid_range_str = _format_port_range(VALID_PORT_RANGE)
        err_msg = (
            f"The port range derived from --base-port ({required_range_str}) must fall within"
            f" the range of valid ports ({valid_range_str})."
        )
        raise ValueError(err_msg)
