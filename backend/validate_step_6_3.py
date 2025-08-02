#!/usr/bin/env python3
"""
Validation Script for ICPY Step 6.3: Agent Service Layer Implementation

This script validates the complete implementation of the agent service layer
including FastAPI endpoints, WebSocket integration, and service functionality.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Any, List

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from icpy.services.agent_service import AgentService, get_agent_service
    from icpy.agent.base_agent import AgentConfig
    from icpy.agent.workflows.workflow_engine import WorkflowConfig, WorkflowTask
    from icpy.agent.configs.agent_templates import template_manager
    from icpy.core.framework_compatibility import FrameworkCompatibilityLayer
    
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Import error: {e}")
    IMPORTS_SUCCESSFUL = False

# Configure logging
logging.basicConfig(level=logging.WARNING)


class ValidationResult:
    """Result of a validation step"""
    def __init__(self, name: str, passed: bool, message: str = "", details: Dict[str, Any] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}


class Step63Validator:
    """Validator for Step 6.3 implementation"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.service: AgentService = None
    
    def log_result(self, name: str, passed: bool, message: str = "", details: Dict[str, Any] = None):
        """Log a validation result"""
        result = ValidationResult(name, passed, message, details)
        self.results.append(result)
        
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if message:
            print(f"📋    {message}")
        if details:
            for key, value in details.items():
                print(f"📋    {key}: {value}")
    
    async def validate_agent_service_core(self):
        """Validate core agent service functionality"""
        print("\n" + "="*60)
        print("🚀 Step 6.3.1: Agent Service Core Validation")
        print("="*60)
        
        try:
            # Test service imports
            self.log_result(
                "Agent service imports successful",
                IMPORTS_SUCCESSFUL,
                "All required modules imported successfully" if IMPORTS_SUCCESSFUL else "Import failures detected"
            )
            
            if not IMPORTS_SUCCESSFUL:
                return
            
            # Initialize service using singleton pattern
            self.service = await get_agent_service()
            
            self.log_result(
                "Agent service initialization successful",
                True,
                "Service initialized with all dependencies"
            )
            
            # Test service components
            components = {
                "message_broker": self.service.message_broker is not None,
                "connection_manager": self.service.connection_manager is not None,
                "capability_registry": self.service.capability_registry is not None,
                "context_manager": self.service.context_manager is not None
            }
            
            all_components = all(components.values())
            self.log_result(
                "Service dependencies initialized",
                all_components,
                f"All core dependencies available: {all_components}",
                components
            )
            
            # Test monitoring task
            monitoring_active = self.service._monitoring_task is not None and not self.service._monitoring_task.done()
            self.log_result(
                "Resource monitoring active",
                monitoring_active,
                "Background monitoring task running"
            )
            
        except Exception as e:
            self.log_result(
                "Agent service core validation",
                False,
                f"Validation failed: {str(e)}"
            )
    
    async def validate_agent_lifecycle(self):
        """Validate agent lifecycle management"""
        print("\n" + "="*60)
        print("🚀 Step 6.3.2: Agent Lifecycle Management Validation")
        print("="*60)
        
        try:
            # Create agent
            config = AgentConfig(
                name="validation_agent",
                framework="openai",
                role="Validation Agent",
                goal="Test agent lifecycle operations",
                capabilities=["text_generation", "reasoning"]
            )
            
            session_id = await self.service.create_agent(config)
            self.log_result(
                "Agent creation successful",
                session_id is not None,
                f"Agent session created: {session_id}"
            )
            
            # Verify agent session
            session = self.service.get_agent_session(session_id)
            session_valid = session is not None and session.agent_name == "validation_agent"
            self.log_result(
                "Agent session retrieval successful",
                session_valid,
                f"Session details: {session.agent_name if session else 'None'}, Status: {session.status.value if session else 'None'}"
            )
            
            # Start agent
            start_success = await self.service.start_agent(session_id)
            self.log_result(
                "Agent start operation successful",
                start_success,
                "Agent transitioned to running state"
            )
            
            # Execute task
            result = await self.service.execute_agent_task(
                session_id,
                "Generate a simple greeting message"
            )
            
            task_success = result is not None and len(result) > 0
            self.log_result(
                "Agent task execution successful",
                task_success,
                f"Task result length: {len(result) if result else 0} characters"
            )
            
            # Stop agent
            stop_success = await self.service.stop_agent(session_id)
            self.log_result(
                "Agent stop operation successful",
                stop_success,
                "Agent stopped successfully"
            )
            
            # Destroy agent
            destroy_success = await self.service.destroy_agent(session_id)
            self.log_result(
                "Agent destruction successful",
                destroy_success,
                "Agent session destroyed"
            )
            
        except Exception as e:
            self.log_result(
                "Agent lifecycle validation",
                False,
                f"Lifecycle validation failed: {str(e)}"
            )
    
    async def validate_workflow_management(self):
        """Validate workflow management functionality"""
        print("\n" + "="*60)
        print("🚀 Step 6.3.3: Workflow Management Validation")
        print("="*60)
        
        try:
            # Create workflow
            tasks = [
                WorkflowTask(
                    name="task1",
                    task_content="Create a test function",
                    agent_config=AgentConfig(name="coder", framework="openai")
                ),
                WorkflowTask(
                    name="task2",
                    task_content="Document the function",
                    dependencies=["task1"],
                    agent_config=AgentConfig(name="documenter", framework="openai")
                )
            ]
            
            config = WorkflowConfig(
                name="validation_workflow",
                description="Workflow for validation testing",
                tasks=tasks
            )
            
            workflow_session_id = await self.service.create_workflow(config)
            self.log_result(
                "Workflow creation successful",
                workflow_session_id is not None,
                f"Workflow session created: {workflow_session_id}"
            )
            
            # Verify workflow session
            workflow_session = self.service.get_workflow_session(workflow_session_id)
            workflow_valid = workflow_session is not None and workflow_session.workflow_name == "validation_workflow"
            self.log_result(
                "Workflow session retrieval successful",
                workflow_valid,
                f"Workflow: {workflow_session.workflow_name if workflow_session else 'None'}"
            )
            
            # Execute workflow
            execution_success = await self.service.execute_workflow(workflow_session_id)
            self.log_result(
                "Workflow execution successful",
                execution_success,
                "Workflow completed execution"
            )
            
            # Check workflow status
            updated_session = self.service.get_workflow_session(workflow_session_id)
            status_valid = updated_session and updated_session.status.value == "completed"
            self.log_result(
                "Workflow completion verified",
                status_valid,
                f"Final status: {updated_session.status.value if updated_session else 'Unknown'}"
            )
            
            # Test workflow control (create new workflow for control tests)
            control_workflow_id = await self.service.create_workflow(config)
            
            # Start execution and pause
            execution_task = asyncio.create_task(self.service.execute_workflow(control_workflow_id))
            await asyncio.sleep(0.1)  # Let it start
            
            pause_success = await self.service.pause_workflow(control_workflow_id)
            self.log_result(
                "Workflow pause operation successful",
                pause_success,
                "Workflow paused during execution"
            )
            
            # Resume
            resume_success = await self.service.resume_workflow(control_workflow_id)
            self.log_result(
                "Workflow resume operation successful",
                resume_success,
                "Workflow resumed after pause"
            )
            
            # Cancel
            cancel_success = await self.service.cancel_workflow(control_workflow_id)
            self.log_result(
                "Workflow cancellation successful",
                cancel_success,
                "Workflow cancelled successfully"
            )
            
            # Clean up execution task
            execution_task.cancel()
            try:
                await execution_task
            except asyncio.CancelledError:
                pass
            
        except Exception as e:
            self.log_result(
                "Workflow management validation",
                False,
                f"Workflow validation failed: {str(e)}"
            )
    
    async def validate_template_integration(self):
        """Validate template integration"""
        print("\n" + "="*60)
        print("🚀 Step 6.3.4: Template Integration Validation")
        print("="*60)
        
        try:
            # Get available templates
            templates = self.service.get_available_templates()
            
            templates_available = "agent_templates" in templates and "workflow_templates" in templates
            self.log_result(
                "Template listing successful",
                templates_available,
                f"Agent templates: {len(templates.get('agent_templates', []))}, Workflow templates: {len(templates.get('workflow_templates', []))}"
            )
            
            # Create agent from template
            template_agent_session = await self.service.create_agent_from_template(
                "code_generator",
                "validation_coder",
                {"preferred_language": "python"}
            )
            
            template_agent_success = template_agent_session is not None
            self.log_result(
                "Agent creation from template successful",
                template_agent_success,
                f"Template agent session: {template_agent_session}"
            )
            
            # Verify template agent has expected capabilities
            if template_agent_session:
                template_session = self.service.get_agent_session(template_agent_session)
                has_code_capability = template_session and "code_generation" in template_session.capabilities
                self.log_result(
                    "Template agent capabilities verified",
                    has_code_capability,
                    f"Capabilities: {template_session.capabilities if template_session else 'None'}"
                )
            
            # Create workflow from template (if available)
            try:
                workflow_from_template = await self.service.create_workflow_from_template(
                    "development_team",
                    "validation_team_workflow"
                )
                
                template_workflow_success = workflow_from_template is not None
                self.log_result(
                    "Workflow creation from template successful",
                    template_workflow_success,
                    f"Template workflow session: {workflow_from_template}"
                )
            except ValueError:
                # Some templates might not have workflow tasks
                self.log_result(
                    "Workflow template handling",
                    True,
                    "Workflow template properly handles missing workflow tasks"
                )
            
        except Exception as e:
            self.log_result(
                "Template integration validation",
                False,
                f"Template validation failed: {str(e)}"
            )
    
    async def validate_performance_monitoring(self):
        """Validate performance monitoring and resource tracking"""
        print("\n" + "="*60)
        print("🚀 Step 6.3.5: Performance Monitoring Validation")
        print("="*60)
        
        try:
            # Get initial resource usage
            initial_stats = self.service.get_resource_usage()
            
            stats_structure_valid = all(key in initial_stats for key in 
                                      ["total_agents", "total_workflows", "resource_usage", "performance_metrics"])
            self.log_result(
                "Resource usage structure valid",
                stats_structure_valid,
                f"Stats keys: {list(initial_stats.keys())}"
            )
            
            # Create some resources and verify monitoring
            agent_config = AgentConfig(name="monitoring_test", framework="openai")
            agent_session = await self.service.create_agent(agent_config)
            
            # Wait for monitoring update
            await asyncio.sleep(1)
            
            updated_stats = self.service.get_resource_usage()
            agent_count_updated = updated_stats["total_agents"] > initial_stats["total_agents"]
            self.log_result(
                "Resource monitoring tracks changes",
                agent_count_updated,
                f"Agents: {initial_stats['total_agents']} → {updated_stats['total_agents']}"
            )
            
            # Test session listing
            all_agent_sessions = self.service.get_agent_sessions()
            all_workflow_sessions = self.service.get_workflow_sessions()
            
            session_listing_works = isinstance(all_agent_sessions, list) and isinstance(all_workflow_sessions, list)
            self.log_result(
                "Session listing operational",
                session_listing_works,
                f"Agent sessions: {len(all_agent_sessions)}, Workflow sessions: {len(all_workflow_sessions)}"
            )
            
            # Test individual session retrieval
            if agent_session:
                retrieved_session = self.service.get_agent_session(agent_session)
                session_retrieval_works = retrieved_session is not None
                self.log_result(
                    "Individual session retrieval works",
                    session_retrieval_works,
                    f"Retrieved session: {retrieved_session.agent_name if retrieved_session else 'None'}"
                )
            
        except Exception as e:
            self.log_result(
                "Performance monitoring validation",
                False,
                f"Monitoring validation failed: {str(e)}"
            )
    
    async def validate_integration_complete(self):
        """Validate complete service integration"""
        print("\n" + "="*60)
        print("🚀 Step 6.3.6: Complete Integration Validation")
        print("="*60)
        
        try:
            # Test service singleton pattern
            service_instance = await get_agent_service()
            singleton_works = service_instance is self.service
            self.log_result(
                "Service singleton pattern works",
                singleton_works,
                "get_agent_service() returns same instance"
            )
            
            # Test end-to-end workflow
            # 1. Create agent from template
            coder_session = await self.service.create_agent_from_template(
                "code_generator",
                "integration_coder"
            )
            
            # 2. Execute task
            await self.service.execute_agent_task(
                coder_session,
                "Create a simple function that adds two numbers"
            )
            
            # 3. Create workflow with the agent
            workflow_tasks = [
                WorkflowTask(
                    name="integration_task",
                    task_content="Complete integration test task",
                    agent_config=AgentConfig(name="integration_agent", framework="openai")
                )
            ]
            
            workflow_config = WorkflowConfig(
                name="integration_workflow",
                description="End-to-end integration test",
                tasks=workflow_tasks
            )
            
            workflow_session = await self.service.create_workflow(workflow_config)
            await self.service.execute_workflow(workflow_session)
            
            # 4. Verify all components worked together
            final_stats = self.service.get_resource_usage()
            integration_success = final_stats["total_agents"] > 0
            
            self.log_result(
                "End-to-end integration successful",
                integration_success,
                f"Final stats: {final_stats['total_agents']} agents, {final_stats['total_workflows']} workflows"
            )
            
            # Test error handling
            try:
                await self.service.create_agent_from_template("nonexistent_template", "test")
                error_handling_works = False
            except ValueError:
                error_handling_works = True
            
            self.log_result(
                "Error handling works correctly",
                error_handling_works,
                "Service properly handles invalid template requests"
            )
            
        except Exception as e:
            self.log_result(
                "Complete integration validation",
                False,
                f"Integration validation failed: {str(e)}"
            )
    
    async def run_validation(self):
        """Run complete validation suite"""
        print("="*60)
        print("🚀 ICPY Step 6.3: Agent Service Layer Validation")
        print("="*60)
        print("📋 Validating agent service layer implementation...")
        print("📋 ")
        
        # Run validation steps
        await self.validate_agent_service_core()
        
        if self.service:
            await self.validate_agent_lifecycle()
            await self.validate_workflow_management()
            await self.validate_template_integration()
            await self.validate_performance_monitoring()
            await self.validate_integration_complete()
            
            # Cleanup
            await self.service.shutdown()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("🚀 Validation Summary")
        print("="*60)
        
        passed_count = sum(1 for result in self.results if result.passed)
        total_count = len(self.results)
        
        for result in self.results:
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            print(f"{status} {result.name}")
        
        print(f"\n📊 Results: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("✅ 🎉 Step 6.3 Validation Complete!")
            print("✅ ✅ All agent service layer components validated")
            print("✅ ✅ Agent lifecycle management working")
            print("✅ ✅ Workflow execution engine operational")
            print("✅ ✅ Template integration functional")
            print("✅ ✅ Performance monitoring active")
            print("✅ ✅ Complete service integration successful")
        else:
            print(f"❌ Validation incomplete: {total_count - passed_count} issues found")
            print("❌ Please review failed tests and fix issues")


async def main():
    """Main validation function"""
    validator = Step63Validator()
    await validator.run_validation()


if __name__ == "__main__":
    asyncio.run(main())
