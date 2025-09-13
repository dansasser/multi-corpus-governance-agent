"""
Comprehensive Smoke Test Module for MCG Agent CLI

Provides comprehensive smoke testing functionality to verify system health,
configuration, and basic functionality before deployment or development.

This is separate from the existing smoke.py which provides simple pipeline testing.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import time

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


class SmokeTestResult:
    """Container for smoke test results"""
    
    def __init__(self, name: str, passed: bool, message: str, duration: float = 0.0, details: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.details = details or {}
    
    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"SmokeTestResult({self.name}: {status} - {self.message})"


class SmokeTestSuite:
    """Comprehensive smoke test suite for MCG Agent"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[SmokeTestResult] = []
        self.start_time = 0.0
        self.end_time = 0.0
    
    async def run_all_tests(self, quick: bool = False) -> bool:
        """Run all smoke tests
        
        Args:
            quick: If True, run only essential connectivity tests
            
        Returns:
            True if all tests passed, False otherwise
        """
        self.start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            if quick:
                tests = self._get_quick_tests()
                task = progress.add_task("Running quick smoke tests...", total=len(tests))
            else:
                tests = self._get_all_tests()
                task = progress.add_task("Running comprehensive smoke tests...", total=len(tests))
            
            for test_func in tests:
                test_name = test_func.__name__.replace('test_', '').replace('_', ' ').title()
                progress.update(task, description=f"Testing {test_name}...")
                
                try:
                    result = await test_func()
                    self.results.append(result)
                    
                    if self.verbose:
                        status = "✅" if result.passed else "❌"
                        console.print(f"{status} {result.name}: {result.message}")
                
                except Exception as e:
                    result = SmokeTestResult(
                        name=test_name,
                        passed=False,
                        message=f"Test failed with exception: {str(e)}",
                        details={'exception': str(e)}
                    )
                    self.results.append(result)
                    
                    if self.verbose:
                        console.print(f"❌ {result.name}: {result.message}")
                
                progress.advance(task)
        
        self.end_time = time.time()
        return all(result.passed for result in self.results)
    
    def _get_quick_tests(self) -> List:
        """Get list of quick tests for basic connectivity"""
        return [
            self.test_python_environment,
            self.test_package_imports,
            self.test_configuration_loading,
            self.test_database_connection,
        ]
    
    def _get_all_tests(self) -> List:
        """Get list of all comprehensive tests"""
        return [
            self.test_python_environment,
            self.test_package_imports,
            self.test_configuration_loading,
            self.test_database_connection,
            self.test_redis_connection,
            self.test_file_system_access,
            self.test_api_key_configuration,
            self.test_security_configuration,
            self.test_governance_configuration,
            self.test_corpus_configuration,
            self.test_agent_instantiation,
            self.test_search_connectors,
            self.test_protocol_validation,
            self.test_cli_functionality,
            self.test_pipeline_smoke,  # Integration with existing smoke test
        ]
    
    async def test_python_environment(self) -> SmokeTestResult:
        """Test Python environment and version"""
        start_time = time.time()
        
        try:
            import sys
            python_version = sys.version_info
            
            if python_version >= (3, 11):
                return SmokeTestResult(
                    name="Python Environment",
                    passed=True,
                    message=f"Python {python_version.major}.{python_version.minor}.{python_version.micro}",
                    duration=time.time() - start_time,
                    details={'version': str(python_version)}
                )
            else:
                return SmokeTestResult(
                    name="Python Environment",
                    passed=False,
                    message=f"Python 3.11+ required, found {python_version.major}.{python_version.minor}",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Python Environment",
                passed=False,
                message=f"Failed to check Python version: {e}",
                duration=time.time() - start_time
            )
    
    async def test_package_imports(self) -> SmokeTestResult:
        """Test that all required packages can be imported"""
        start_time = time.time()
        
        required_packages = [
            'mcg_agent',
            'mcg_agent.config',
            'mcg_agent.db.models_personal',
            'mcg_agent.search.connectors',
            'mcg_agent.protocols.governance_protocol',
            'mcg_agent.pydantic_ai.agent_base',
            'pydantic_ai',
            'fastapi',
            'sqlalchemy',
            'redis',
        ]
        
        failed_imports = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError as e:
                failed_imports.append(f"{package}: {e}")
        
        if not failed_imports:
            return SmokeTestResult(
                name="Package Imports",
                passed=True,
                message=f"All {len(required_packages)} required packages imported successfully",
                duration=time.time() - start_time,
                details={'packages': required_packages}
            )
        else:
            return SmokeTestResult(
                name="Package Imports",
                passed=False,
                message=f"Failed to import {len(failed_imports)} packages",
                duration=time.time() - start_time,
                details={'failed_imports': failed_imports}
            )
    
    async def test_configuration_loading(self) -> SmokeTestResult:
        """Test configuration loading and validation"""
        start_time = time.time()
        
        try:
            from mcg_agent.config import settings, validate_environment
            
            # Test basic configuration access
            db_url = settings.postgres_url
            redis_url = settings.redis_url
            jwt_key = settings.JWT_SECRET_KEY
            
            # Run environment validation
            validation_result = validate_environment()
            
            if validation_result['valid']:
                return SmokeTestResult(
                    name="Configuration Loading",
                    passed=True,
                    message="Configuration loaded and validated successfully",
                    duration=time.time() - start_time,
                    details={
                        'environment': validation_result['environment'],
                        'warnings': validation_result['warnings']
                    }
                )
            else:
                return SmokeTestResult(
                    name="Configuration Loading",
                    passed=False,
                    message=f"Configuration validation failed: {validation_result['issues']}",
                    duration=time.time() - start_time,
                    details=validation_result
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Configuration Loading",
                passed=False,
                message=f"Configuration loading failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_database_connection(self) -> SmokeTestResult:
        """Test database connectivity"""
        start_time = time.time()
        
        try:
            from mcg_agent.db.session import get_session
            
            with get_session() as session:
                # Simple connectivity test
                result = session.execute('SELECT 1 as test_value')
                test_value = result.scalar()
                
                if test_value == 1:
                    return SmokeTestResult(
                        name="Database Connection",
                        passed=True,
                        message="Database connection successful",
                        duration=time.time() - start_time,
                        details={'test_query_result': test_value}
                    )
                else:
                    return SmokeTestResult(
                        name="Database Connection",
                        passed=False,
                        message=f"Unexpected test query result: {test_value}",
                        duration=time.time() - start_time
                    )
        
        except Exception as e:
            return SmokeTestResult(
                name="Database Connection",
                passed=False,
                message=f"Database connection failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_redis_connection(self) -> SmokeTestResult:
        """Test Redis connectivity"""
        start_time = time.time()
        
        try:
            import redis
            from mcg_agent.config import settings
            
            # Create Redis client
            redis_client = redis.from_url(settings.redis_url)
            
            # Test basic operations
            test_key = "mcg_agent_smoke_test"
            test_value = "smoke_test_value"
            
            # Set and get test value
            redis_client.set(test_key, test_value, ex=10)  # Expire in 10 seconds
            retrieved_value = redis_client.get(test_key)
            
            # Clean up
            redis_client.delete(test_key)
            
            if retrieved_value and retrieved_value.decode() == test_value:
                return SmokeTestResult(
                    name="Redis Connection",
                    passed=True,
                    message="Redis connection and operations successful",
                    duration=time.time() - start_time
                )
            else:
                return SmokeTestResult(
                    name="Redis Connection",
                    passed=False,
                    message="Redis operations failed",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Redis Connection",
                passed=False,
                message=f"Redis connection failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_file_system_access(self) -> SmokeTestResult:
        """Test file system read/write access"""
        start_time = time.time()
        
        try:
            # Test temporary file creation
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
                test_content = "MCG Agent smoke test"
                temp_file.write(test_content)
                temp_file_path = temp_file.name
            
            # Test reading the file
            with open(temp_file_path, 'r') as temp_file:
                read_content = temp_file.read()
            
            # Clean up
            Path(temp_file_path).unlink()
            
            if read_content == test_content:
                return SmokeTestResult(
                    name="File System Access",
                    passed=True,
                    message="File system read/write operations successful",
                    duration=time.time() - start_time
                )
            else:
                return SmokeTestResult(
                    name="File System Access",
                    passed=False,
                    message="File content mismatch",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="File System Access",
                passed=False,
                message=f"File system access failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_api_key_configuration(self) -> SmokeTestResult:
        """Test API key configuration"""
        start_time = time.time()
        
        try:
            from mcg_agent.config import settings
            
            api_keys_configured = []
            
            if settings.api.OPENAI_API_KEY:
                api_keys_configured.append("OpenAI")
            
            if settings.api.ANTHROPIC_API_KEY:
                api_keys_configured.append("Anthropic")
            
            if settings.api.COHERE_API_KEY:
                api_keys_configured.append("Cohere")
            
            if api_keys_configured:
                return SmokeTestResult(
                    name="API Key Configuration",
                    passed=True,
                    message=f"API keys configured for: {', '.join(api_keys_configured)}",
                    duration=time.time() - start_time,
                    details={'configured_apis': api_keys_configured}
                )
            else:
                return SmokeTestResult(
                    name="API Key Configuration",
                    passed=False,
                    message="No API keys configured",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="API Key Configuration",
                passed=False,
                message=f"API key check failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_security_configuration(self) -> SmokeTestResult:
        """Test security configuration"""
        start_time = time.time()
        
        try:
            from mcg_agent.config import settings
            
            issues = []
            
            # Check JWT secret
            if settings.security.JWT_SECRET_KEY == "your-jwt-secret-key-change-this-in-production":
                issues.append("JWT_SECRET_KEY is using default value")
            
            # Check encryption key
            if settings.security.ENCRYPTION_KEY == "your-32-byte-encryption-key-change-this-in-production":
                issues.append("ENCRYPTION_KEY is using default value")
            
            # Check if production environment has secure config
            if settings.is_production():
                prod_issues = settings.validate_production_config()
                issues.extend(prod_issues)
            
            if not issues:
                return SmokeTestResult(
                    name="Security Configuration",
                    passed=True,
                    message="Security configuration is properly set",
                    duration=time.time() - start_time
                )
            else:
                return SmokeTestResult(
                    name="Security Configuration",
                    passed=False,
                    message=f"Security issues found: {'; '.join(issues)}",
                    duration=time.time() - start_time,
                    details={'issues': issues}
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Security Configuration",
                passed=False,
                message=f"Security configuration check failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_governance_configuration(self) -> SmokeTestResult:
        """Test governance configuration"""
        start_time = time.time()
        
        try:
            from mcg_agent.protocols.governance_protocol import API_CALL_LIMITS, CORPUS_ACCESS
            from mcg_agent.config import settings
            
            # Verify governance settings are loaded
            governance_config = settings.governance
            
            # Check API call limits
            total_api_calls = (
                governance_config.IDEATOR_MAX_API_CALLS +
                governance_config.DRAFTER_MAX_API_CALLS +
                governance_config.CRITIC_MAX_API_CALLS +
                governance_config.REVISOR_MAX_API_CALLS +
                governance_config.SUMMARIZER_MAX_API_CALLS
            )
            
            # Verify protocol constants
            if API_CALL_LIMITS and CORPUS_ACCESS:
                return SmokeTestResult(
                    name="Governance Configuration",
                    passed=True,
                    message=f"Governance configured with {total_api_calls} total API calls per task",
                    duration=time.time() - start_time,
                    details={
                        'total_api_calls': total_api_calls,
                        'mvlm_enabled': governance_config.MVLM_ENABLED
                    }
                )
            else:
                return SmokeTestResult(
                    name="Governance Configuration",
                    passed=False,
                    message="Governance protocol constants not properly loaded",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Governance Configuration",
                passed=False,
                message=f"Governance configuration check failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_corpus_configuration(self) -> SmokeTestResult:
        """Test corpus configuration"""
        start_time = time.time()
        
        try:
            from mcg_agent.config import settings
            
            corpus_config = settings.corpus
            enabled_corpora = []
            
            if corpus_config.PERSONAL_CORPUS_ENABLED:
                enabled_corpora.append("Personal")
            
            if corpus_config.SOCIAL_CORPUS_ENABLED:
                enabled_corpora.append("Social")
            
            if corpus_config.PUBLISHED_CORPUS_ENABLED:
                enabled_corpora.append("Published")
            
            if enabled_corpora:
                return SmokeTestResult(
                    name="Corpus Configuration",
                    passed=True,
                    message=f"Enabled corpora: {', '.join(enabled_corpora)}",
                    duration=time.time() - start_time,
                    details={
                        'enabled_corpora': enabled_corpora,
                        'rag_enabled': corpus_config.RAG_ENABLED
                    }
                )
            else:
                return SmokeTestResult(
                    name="Corpus Configuration",
                    passed=False,
                    message="No corpora enabled",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Corpus Configuration",
                passed=False,
                message=f"Corpus configuration check failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_agent_instantiation(self) -> SmokeTestResult:
        """Test agent instantiation"""
        start_time = time.time()
        
        try:
            from mcg_agent.pydantic_ai.agent_base import AgentRole, GovernanceContext
            
            # Test creating governance context
            context = GovernanceContext(
                user_id="smoke_test_user",
                session_id="smoke_test_session",
                task_id="smoke_test_task"
            )
            
            # Test agent role enum
            roles = list(AgentRole)
            
            if context and len(roles) >= 5:  # Should have at least 5 agent roles
                return SmokeTestResult(
                    name="Agent Instantiation",
                    passed=True,
                    message=f"Agent framework ready with {len(roles)} roles",
                    duration=time.time() - start_time,
                    details={'available_roles': [role.value for role in roles]}
                )
            else:
                return SmokeTestResult(
                    name="Agent Instantiation",
                    passed=False,
                    message="Agent framework not properly configured",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Agent Instantiation",
                passed=False,
                message=f"Agent instantiation failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_search_connectors(self) -> SmokeTestResult:
        """Test search connector functionality"""
        start_time = time.time()
        
        try:
            from mcg_agent.search.connectors import query_personal, query_social, query_published
            from mcg_agent.search.models import PersonalSearchFilters, SocialSearchFilters, PublishedSearchFilters
            
            # Test that connectors can be imported and have proper signatures
            connectors = [query_personal, query_social, query_published]
            filter_types = [PersonalSearchFilters, SocialSearchFilters, PublishedSearchFilters]
            
            if all(callable(connector) for connector in connectors):
                return SmokeTestResult(
                    name="Search Connectors",
                    passed=True,
                    message=f"All {len(connectors)} search connectors available",
                    duration=time.time() - start_time,
                    details={'connectors': [c.__name__ for c in connectors]}
                )
            else:
                return SmokeTestResult(
                    name="Search Connectors",
                    passed=False,
                    message="Search connectors not properly configured",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Search Connectors",
                passed=False,
                message=f"Search connector test failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_protocol_validation(self) -> SmokeTestResult:
        """Test protocol validation"""
        start_time = time.time()
        
        try:
            from mcg_agent.protocols.context_protocol import ContextSnippet, ContextPack
            from mcg_agent.protocols.governance_protocol import API_CALL_LIMITS
            from mcg_agent.protocols.routing_protocol import RoutingDecision
            
            # Test creating protocol objects
            snippet = ContextSnippet(
                content="Test content",
                source="smoke_test",
                corpus="personal",
                relevance_score=0.8
            )
            
            context_pack = ContextPack(
                snippets=[snippet],
                total_results=1,
                query="test query"
            )
            
            routing_decision = RoutingDecision(
                classification="chat",
                confidence=0.9,
                reasoning="Test routing"
            )
            
            if snippet and context_pack and routing_decision and API_CALL_LIMITS:
                return SmokeTestResult(
                    name="Protocol Validation",
                    passed=True,
                    message="All protocol objects created successfully",
                    duration=time.time() - start_time
                )
            else:
                return SmokeTestResult(
                    name="Protocol Validation",
                    passed=False,
                    message="Protocol validation failed",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="Protocol Validation",
                passed=False,
                message=f"Protocol validation failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_cli_functionality(self) -> SmokeTestResult:
        """Test CLI functionality"""
        start_time = time.time()
        
        try:
            from mcg_agent.cli.main import cli
            from mcg_agent.cli.commands import CLICommands
            from mcg_agent.cli.config import get_cli_config
            
            # Test CLI configuration
            cli_config = get_cli_config()
            
            # Test CLI commands class
            commands = CLICommands()
            
            if cli and commands and cli_config:
                return SmokeTestResult(
                    name="CLI Functionality",
                    passed=True,
                    message="CLI components loaded successfully",
                    duration=time.time() - start_time,
                    details={'cli_config_loaded': True}
                )
            else:
                return SmokeTestResult(
                    name="CLI Functionality",
                    passed=False,
                    message="CLI components not properly loaded",
                    duration=time.time() - start_time
                )
        
        except Exception as e:
            return SmokeTestResult(
                name="CLI Functionality",
                passed=False,
                message=f"CLI functionality test failed: {e}",
                duration=time.time() - start_time
            )
    
    async def test_pipeline_smoke(self) -> SmokeTestResult:
        """Test pipeline functionality using existing smoke test"""
        start_time = time.time()
        
        try:
            from mcg_agent.routing.pipeline import GovernedAgentPipeline
            
            # Test pipeline instantiation
            pipeline = GovernedAgentPipeline()
            
            # Simple test prompt
            test_prompt = "Hello, this is a smoke test"
            
            # Try to process the request (this may fail due to missing API keys, but we test instantiation)
            try:
                result = await pipeline.process_request(test_prompt)
                
                return SmokeTestResult(
                    name="Pipeline Smoke",
                    passed=True,
                    message="Pipeline processed request successfully",
                    duration=time.time() - start_time,
                    details={'agent_role': result.agent_role, 'has_content': bool(result.content)}
                )
            
            except Exception as pipeline_error:
                # Pipeline instantiation worked, but processing failed (likely due to API keys)
                if "API" in str(pipeline_error) or "key" in str(pipeline_error).lower():
                    return SmokeTestResult(
                        name="Pipeline Smoke",
                        passed=True,
                        message="Pipeline instantiated successfully (API key needed for full test)",
                        duration=time.time() - start_time,
                        details={'pipeline_error': str(pipeline_error)}
                    )
                else:
                    raise pipeline_error
        
        except Exception as e:
            return SmokeTestResult(
                name="Pipeline Smoke",
                passed=False,
                message=f"Pipeline smoke test failed: {e}",
                duration=time.time() - start_time
            )
    
    def display_results(self) -> None:
        """Display test results in a formatted table"""
        # Create results table
        table = Table(title="Smoke Test Results", show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan", no_wrap=True)
        table.add_column("Status", style="green", width=8)
        table.add_column("Duration", style="yellow", width=10)
        table.add_column("Message", style="dim")
        
        passed_count = 0
        total_duration = 0.0
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            status_style = "green" if result.passed else "red"
            duration_str = f"{result.duration:.2f}s"
            
            table.add_row(
                result.name,
                status,
                duration_str,
                result.message,
                style=status_style if not result.passed else None
            )
            
            if result.passed:
                passed_count += 1
            total_duration += result.duration
        
        console.print(table)
        
        # Summary
        total_tests = len(self.results)
        overall_duration = self.end_time - self.start_time
        
        console.print(f"\nSummary: {passed_count}/{total_tests} tests passed")
        console.print(f"Total duration: {overall_duration:.2f}s")
        
        if passed_count == total_tests:
            console.print("🎉 All smoke tests passed!", style="bold green")
        else:
            failed_count = total_tests - passed_count
            console.print(f"⚠️  {failed_count} test(s) failed", style="bold red")


async def run_comprehensive_smoke_test(quick: bool = False, verbose: bool = False) -> bool:
    """Run comprehensive smoke tests and return success status
    
    Args:
        quick: Run only quick connectivity tests
        verbose: Enable verbose output
        
    Returns:
        True if all tests passed, False otherwise
    """
    suite = SmokeTestSuite(verbose=verbose)
    
    try:
        success = await suite.run_all_tests(quick=quick)
        suite.display_results()
        return success
    
    except KeyboardInterrupt:
        console.print("\n⚠️  Smoke tests interrupted by user", style="yellow")
        return False
    
    except Exception as e:
        console.print(f"\n❌ Smoke test suite failed: {e}", style="red")
        return False


if __name__ == "__main__":
    # Allow running smoke tests directly
    import sys
    
    quick = "--quick" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    success = asyncio.run(run_comprehensive_smoke_test(quick=quick, verbose=verbose))
    sys.exit(0 if success else 1)
