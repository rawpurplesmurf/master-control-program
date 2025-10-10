"""
Test intelligent template selection system
"""
import pytest
from unittest.mock import Mock, patch
from mcp.command_processor import determine_prompt_template


class TestIntelligentTemplateSelection:
    """Test cases for intelligent prompt template selection based on keywords."""
    
    def create_mock_template(self, name, keywords):
        """Helper to create mock template objects."""
        template = Mock()
        template.template_name = name
        template.intent_keywords = keywords
        return template
    
    def test_home_automation_selection(self):
        """Test that home automation commands select the right template."""
        mock_templates = [
            self.create_mock_template("default", "general, help"),
            self.create_mock_template("home_automation", "turn, switch, set, adjust, control"),
            self.create_mock_template("information", "what, when, where, how")
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # Test various home automation commands
        assert determine_prompt_template("turn on the lights", mock_db) == "home_automation"
        assert determine_prompt_template("switch off the fan", mock_db) == "home_automation"
        assert determine_prompt_template("set temperature to 72", mock_db) == "home_automation"
        assert determine_prompt_template("adjust the brightness please", mock_db) == "home_automation"
        assert determine_prompt_template("control the music system", mock_db) == "home_automation"
    
    def test_information_query_selection(self):
        """Test that information queries select the right template."""
        mock_templates = [
            self.create_mock_template("default", "general, help"),
            self.create_mock_template("home_automation", "turn, switch, set"),
            self.create_mock_template("information", "what, when, where, how, why")
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # Test various information queries
        assert determine_prompt_template("what lights are on", mock_db) == "information"
        assert determine_prompt_template("when was the alarm", mock_db) == "information"
        assert determine_prompt_template("where is my phone", mock_db) == "information"
        assert determine_prompt_template("how many devices active", mock_db) == "information"
        assert determine_prompt_template("why is the temperature", mock_db) == "information"
    
    def test_tie_breaking_by_specificity(self):
        """Test that more specific templates (more keywords) win in ties."""
        mock_templates = [
            self.create_mock_template("simple", "turn, switch"),  # 2 keywords
            self.create_mock_template("detailed", "turn, switch, set, adjust, control, dim"),  # 6 keywords
            self.create_mock_template("basic", "turn")  # 1 keyword
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # All templates match "turn", but "detailed" should win due to more total keywords
        result = determine_prompt_template("turn on lights", mock_db)
        assert result == "detailed"
    
    def test_multiple_keyword_matches(self):
        """Test that templates with more matched keywords win."""
        mock_templates = [
            self.create_mock_template("single_match", "turn, other, keywords"),
            self.create_mock_template("double_match", "turn, the, more, keywords"),
            self.create_mock_template("no_match", "different, unrelated, words")
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # "turn the lights" should match both "turn" and "the" in double_match template
        result = determine_prompt_template("turn the lights on", mock_db)
        assert result == "double_match"
    
    def test_default_fallback(self):
        """Test that default template is used when no keywords match."""
        mock_templates = [
            self.create_mock_template("default", "general, help"),
            self.create_mock_template("home_automation", "turn, switch, set"),
            self.create_mock_template("information", "what, when, where")
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # Command with no matching keywords should use default
        result = determine_prompt_template("hello there friend", mock_db)
        assert result == "default"
    
    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        mock_templates = [
            self.create_mock_template("automation", "Turn, SWITCH, Set"),
            self.create_mock_template("default", "general")
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # Should match regardless of case
        assert determine_prompt_template("TURN on lights", mock_db) == "automation"
        assert determine_prompt_template("switch OFF fan", mock_db) == "automation"
        assert determine_prompt_template("Set the temperature", mock_db) == "automation"
    
    def test_first_five_words_only(self):
        """Test that only the first 5 words are analyzed."""
        mock_templates = [
            self.create_mock_template("match", "keyword"),
            self.create_mock_template("default", "general")
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # Keyword in position 6+ should not match
        result = determine_prompt_template("one two three four five keyword", mock_db)
        assert result == "default"  # Should not match "keyword" template
        
        # Keyword in first 5 words should match
        result = determine_prompt_template("one two keyword four five six", mock_db)
        assert result == "match"
    
    def test_empty_command_handling(self):
        """Test handling of empty or whitespace-only commands."""
        mock_templates = [
            self.create_mock_template("default", "general"),
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # Empty commands should use default
        assert determine_prompt_template("", mock_db) == "default"
        assert determine_prompt_template("   ", mock_db) == "default"
        assert determine_prompt_template("\n\t", mock_db) == "default"
    
    def test_no_templates_in_database(self):
        """Test handling when no templates exist in database."""
        mock_db = Mock()
        mock_db.query().all.return_value = []
        
        result = determine_prompt_template("any command", mock_db)
        assert result == "default"
    
    def test_templates_without_keywords(self):
        """Test handling of templates that have no intent keywords."""
        mock_templates = [
            self.create_mock_template("no_keywords", None),
            self.create_mock_template("empty_keywords", ""),
            self.create_mock_template("with_keywords", "turn, switch")
        ]
        
        mock_db = Mock()
        mock_db.query().all.return_value = mock_templates
        
        # Should match the template with keywords
        result = determine_prompt_template("turn on lights", mock_db)
        assert result == "with_keywords"
    
    def test_database_error_handling(self):
        """Test that database errors fall back to default template."""
        mock_db = Mock()
        mock_db.query().all.side_effect = Exception("Database error")
        
        result = determine_prompt_template("any command", mock_db)
        assert result == "default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])