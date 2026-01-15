import pytest
import json
from pathlib import Path
from flux_studio.agents.agent_registry import AgentRegistry
from flux_studio.agents.agent_protocol import AgentConfig

@pytest.fixture
def workspace(tmp_path):
    registry = AgentRegistry(tmp_path)
    registry.init_workspace_sync()
    return registry, tmp_path

@pytest.mark.asyncio
async def test_agent_config_loading(workspace):
    registry, tmp_path = workspace

    # Create a flux_agents.json
    config = {
        "version": "1.0",
        "agents": [
            {
                "id": "agent-1",
                "name": "Test Agent 1",
                "command": ["python", "-m", "agent1"],
                "env": {"KEY": "VALUE"},
                "description": "First agent"
            },
            {
                "id": "agent-2",
                "name": "Test Agent 2",
                "command": ["python", "-m", "agent2"]
            }
        ]
    }

    config_path = tmp_path / ".flux-studio" / "flux_agents.json"
    with open(config_path, "w") as f:
        json.dump(config, f)

    # Load config
    agents = await registry.load_agent_config()

    assert len(agents) == 2
    assert agents[0].id == "agent-1"
    assert agents[0].name == "Test Agent 1"
    assert agents[0].command == ["python", "-m", "agent1"]
    assert agents[0].env == {"KEY": "VALUE"}

    assert agents[1].id == "agent-2"
    assert agents[1].env == {}  # Default empty dict

@pytest.mark.asyncio
async def test_agent_config_missing_file(workspace):
    registry, tmp_path = workspace

    # Ensure no config exists (init_workspace creates an empty one if not present,
    # but let's delete it to test graceful handling or recreation)
    config_path = tmp_path / ".flux-studio" / "flux_agents.json"
    if config_path.exists():
        config_path.unlink()

    agents = await registry.load_agent_config()
    assert len(agents) == 0
    assert config_path.exists()  # Should be recreated with default

@pytest.mark.asyncio
async def test_agent_creation_with_assignment(workspace):
    registry, tmp_path = workspace

    task = await registry.create_task("Do something", assigned_to="agent-1")

    assert task.assigned_to == "agent-1"

    # Verify file content
    task_path = tmp_path / ".flux-studio" / "tasks" / f"task_{task.id}.json"
    with open(task_path) as f:
        data = json.load(f)
        assert data["assigned_to"] == "agent-1"
