from __future__ import annotations

from collections.abc import (
    Callable,
    Iterable,
)
from dataclasses import dataclass

from app.hardware.sensor_reader import (
    HardwareSensorReader,
)


# ============================================================
# EXCEPTIONS
# ============================================================


class HardwareSensorRoutingError(
    RuntimeError
):
    """
    Raised when hardware-adapter routing is ambiguous or the
    registry itself is invalid.
    """


# ============================================================
# ROUTE
# ============================================================


@dataclass(
    frozen=True,
    slots=True,
)
class HardwareSensorReaderRoute:
    """
    One physical hardware-adapter route.

    `matches` decides whether a concrete hardware identifier
    belongs to this reader.

    The matcher must describe the physical device/protocol,
    not the AquaMind measurement role.
    """

    name: str

    matches: Callable[
        [str],
        bool,
    ]

    reader: HardwareSensorReader


# ============================================================
# REGISTRY
# ============================================================


class HardwareSensorReaderRegistry:
    """
    Resolve physical sensor adapters using hardware identifiers.

    Examples:

        28-xxxxxxxxxxxx
            -> DS18B20Reader

    Future adapters can later add their real identifier rules
    when those physical modules are confirmed.

    SensorType is intentionally not used here because it says
    WHAT AquaMind measures, not HOW the device communicates.
    """

    def __init__(
        self,
        routes: Iterable[
            HardwareSensorReaderRoute
        ],
    ) -> None:
        normalized_routes: list[
            HardwareSensorReaderRoute
        ] = []

        names: set[str] = set()

        for route in routes:
            name = (
                route.name
                .strip()
            )

            if not name:
                raise HardwareSensorRoutingError(
                    "Hardware sensor reader route "
                    "name cannot be empty"
                )

            if name in names:
                raise HardwareSensorRoutingError(
                    "Duplicate hardware sensor "
                    f"reader route: {name}"
                )

            names.add(
                name
            )

            normalized_routes.append(
                HardwareSensorReaderRoute(
                    name=name,
                    matches=route.matches,
                    reader=route.reader,
                )
            )

        self._routes = tuple(
            normalized_routes
        )

    # ========================================================
    # RESOLUTION
    # ========================================================

    def resolve(
        self,
        hardware_identifier: (
            str | None
        ),
    ) -> HardwareSensorReader | None:
        if hardware_identifier is None:
            return None

        identifier = (
            hardware_identifier
            .strip()
        )

        if not identifier:
            return None

        matching_routes: list[
            HardwareSensorReaderRoute
        ] = []

        for route in self._routes:
            try:
                matched = bool(
                    route.matches(
                        identifier
                    )
                )

            except Exception as exc:
                raise HardwareSensorRoutingError(
                    "Hardware sensor reader "
                    f"route '{route.name}' failed "
                    "while matching an identifier"
                ) from exc

            if matched:
                matching_routes.append(
                    route
                )

        if not matching_routes:
            return None

        if len(
            matching_routes
        ) > 1:
            names = ", ".join(
                route.name
                for route
                in matching_routes
            )

            raise HardwareSensorRoutingError(
                "Multiple hardware sensor readers "
                "match the same identifier: "
                f"{names}"
            )

        return (
            matching_routes[0]
            .reader
        )