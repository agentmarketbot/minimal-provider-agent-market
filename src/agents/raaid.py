from typing import Any, Dict


def get_container_kwargs() -> Dict[str, Any]:
    """
    Get container configuration for RA.Aid agent
    """
    return {
        "environment": {
            "RAAID_ENABLED": "1",
            # Add any other RA.Aid specific environment variables here
        },
        "volumes": {
            # Add any necessary volume mounts
        },
    }
