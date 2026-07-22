import os
from app.config import get_agent_settings

def test_config_defaults():
    # Clear environment variables if they exist
    for key in list(os.environ.keys()):
        if key.startswith("TEST_AGENT_"):
            del os.environ[key]
            
    model, settings = get_agent_settings("TEST_AGENT", "gpt-default")
    assert model == "gpt-default"
    assert settings.temperature is None
    assert settings.top_p is None
    assert settings.max_tokens is None
    assert settings.extra_args is None

def test_config_custom():
    os.environ["TEST_AGENT_MODEL"] = "gpt-custom"
    os.environ["TEST_AGENT_TEMPERATURE"] = "0.7"
    os.environ["TEST_AGENT_TOP_P"] = "0.9"
    os.environ["TEST_AGENT_TOP_K"] = "50"
    os.environ["TEST_AGENT_MAX_TOKENS"] = "200"
    
    model, settings = get_agent_settings("TEST_AGENT", "gpt-default")
    assert model == "gpt-custom"
    assert settings.temperature == 0.7
    assert settings.top_p == 0.9
    assert settings.max_tokens == 200
    assert settings.extra_args == {"top_k": 50}
    
    # Clean up
    del os.environ["TEST_AGENT_MODEL"]
    del os.environ["TEST_AGENT_TEMPERATURE"]
    del os.environ["TEST_AGENT_TOP_P"]
    del os.environ["TEST_AGENT_TOP_K"]
    del os.environ["TEST_AGENT_MAX_TOKENS"]

if __name__ == "__main__":
    test_config_defaults()
    test_config_custom()
    print("All config tests passed!")
