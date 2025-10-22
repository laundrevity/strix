import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
import logging

from core.Agent import Agent
from core.performance import PerformanceMonitor
from core.reflection import SelfReflectionEngine
from core.safety import SafetyGuardrails
from core.memory import LearningMemory
from local_llm.llm_interface import LocalLLMInterface


class SelfImprovingAgent(Agent):
    """Extended Agent with self-improvement capabilities"""
    
    def __init__(self, prompt: str, snap: bool, enable_self_improvement: bool = True):
        super().__init__(prompt, snap)
        
        self.enable_self_improvement = enable_self_improvement
        self.interaction_count = 0
        self.last_reflection_time = datetime.now()
        
        if enable_self_improvement:
            self.performance_monitor = PerformanceMonitor()
            self.reflection_engine = SelfReflectionEngine()
            self.safety_guardrails = SafetyGuardrails()
            self.learning_memory = LearningMemory()
            
            # Background task for self-improvement
            self.improvement_task: Optional[asyncio.Task] = None
            self._should_stop_improvement = False
            
        self.log.info(f"SelfImprovingAgent initialized with self_improvement={enable_self_improvement}")
    
    async def __aenter__(self):
        await super().__aenter__()
        if self.enable_self_improvement:
            # Start background self-improvement loop
            self.improvement_task = asyncio.create_task(self._self_improvement_loop())
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.enable_self_improvement:
            self._should_stop_improvement = True
            if self.improvement_task:
                self.improvement_task.cancel()
                try:
                    await self.improvement_task
                except asyncio.CancelledError:
                    pass
        await super().__aexit__(exc_type, exc_val, exc_tb)
    
    async def __call__(self):
        """Main interaction loop with enhanced tracking"""
        try:
            while True:
                # Handle user interaction
                response, n_tokens = await self.get_response()
                self.messages.append(response)
                
                # Track interaction for self-improvement
                if self.enable_self_improvement:
                    await self._track_interaction(response)
                
                # Handle tool calls as usual
                while tool_calls := response.get("tool_calls"):
                    tool_coroutines = []
                    tool_call_data = []
                    
                    for tc in tool_calls:
                        fn_name = tc["function"]["name"]
                        tool_call_data.append((tc, fn_name))
                        
                        if fn := self.tools.get(fn_name):
                            kwargs = json.loads(tc["function"]["arguments"])
                            
                            async def execute_tool(tool_func, tool_kwargs):
                                self.log.debug(f"executing tool[{tool_func.__name__}](tool_kwargs[{tool_kwargs}])...")
                                result = tool_func(**tool_kwargs)
                                if asyncio.iscoroutine(result):
                                    result = await result
                                return result
                            
                            tool_coroutines.append(execute_tool(fn, kwargs))
                        else:
                            async def missing_tool():
                                return f"{fn_name} not in tools[{list(self.tools.keys())}]"
                            tool_coroutines.append(missing_tool())
                    
                    tool_results = await asyncio.gather(*tool_coroutines)
                    
                    for (tc, fn_name), res in zip(tool_call_data, tool_results):
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": fn_name,
                            "content": str(res),
                        })
                    
                    response, n_tokens = await self.get_response()
                    self.messages.append(response)
                    
                    if self.enable_self_improvement:
                        await self._track_interaction(response)
                
                # Get user input
                prompt = await self.read(prefix=f"[{n_tokens}] > ")
                self.messages.append({"role": "user", "content": prompt})
                
                self.interaction_count += 1
                
        except Exception as e:
            self.log.error(f"Error in main interaction loop: {e}")
            raise
    
    async def _track_interaction(self, response: dict):
        """Track interaction for performance monitoring"""
        try:
            context = {
                "interaction_count": self.interaction_count,
                "timestamp": datetime.now().isoformat(),
                "response_length": len(response.get("content", "")),
                "tool_calls_made": len(response.get("tool_calls", [])),
                "message_history_length": len(self.messages)
            }
            
            # Extract basic feedback (could be enhanced with explicit user feedback)
            feedback = {
                "response_length_appropriate": len(response.get("content", "")) > 10,
                "tool_usage_efficient": len(response.get("tool_calls", [])) <= 3
            }
            
            await self.performance_monitor.record_interaction(
                prompt=self.messages[-2]["content"] if len(self.messages) > 1 else "",
                response=response.get("content", ""),
                feedback=feedback,
                context=context
            )
            
        except Exception as e:
            self.log.warning(f"Failed to track interaction: {e}")
    
    async def _self_improvement_loop(self):
        """Background loop for periodic self-improvement"""
        while not self._should_stop_improvement:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                if self._should_stop_improvement:
                    break
                
                # Check if enough interactions have occurred
                if self.interaction_count < 10:
                    continue
                
                # Check if enough time has passed since last reflection
                time_since_last_reflection = datetime.now() - self.last_reflection_time
                if time_since_last_reflection < timedelta(hours=6):
                    continue
                
                await self._perform_self_improvement_cycle()
                
            except asyncio.CancelledError:
                self.log.info("Self-improvement loop cancelled")
                break
            except Exception as e:
                self.log.error(f"Error in self-improvement loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _perform_self_improvement_cycle(self):
        """Execute one self-improvement cycle"""
        try:
            self.log.info("Starting self-improvement cycle")
            self.last_reflection_time = datetime.now()
            
            # 1. Analyze recent performance
            metrics = await self.performance_monitor.analyze_trends(
                time_window=timedelta(hours=24)
            )
            
            if not metrics.has_sufficient_data():
                self.log.info("Insufficient data for self-improvement analysis")
                return
            
            # 2. Reflect on performance
            reflection = await self.reflection_engine.analyze_performance(metrics)
            
            # 3. Identify improvement opportunities
            opportunities = await self.reflection_engine.identify_improvement_opportunities(
                reflection
            )
            
            if not opportunities:
                self.log.info("No improvement opportunities identified")
                return
            
            # 4. Create improvement plan
            plan = await self.reflection_engine.generate_improvement_plan(opportunities)
            
            # 5. Execute improvements safely
            improvements_made = []
            for action in plan.actions:
                try:
                    # Safety check
                    safety_result = await self.safety_guardrails.validate_improvement(action)
                    if not safety_result.is_safe:
                        self.log.warning(f"Unsafe improvement blocked: {safety_result.reason}")
                        continue
                    
                    # Execute with monitoring
                    result = await action.execute(plan)
                    if result.success:
                        await self.learning_memory.record_success(
                            context=plan.context,
                            improvement=action
                        )
                        improvements_made.append(action)
                        self.log.info(f"Successfully applied improvement: {action.description}")
                    else:
                        await self.learning_memory.record_failure(
                            context=plan.context,
                            improvement=action,
                            reason=result.error
                        )
                        await action.rollback()
                        self.log.warning(f"Failed improvement rolled back: {result.error}")
                        
                except Exception as e:
                    self.log.error(f"Error executing improvement action: {e}")
                    try:
                        await action.rollback()
                    except Exception as rollback_error:
                        self.log.error(f"Error during rollback: {rollback_error}")
            
            if improvements_made:
                self.log.info(f"Self-improvement cycle completed. Applied {len(improvements_made)} improvements.")
            else:
                self.log.info("Self-improvement cycle completed. No improvements applied.")
                
        except Exception as e:
            self.log.error(f"Error in self-improvement cycle: {e}")
    
    async def trigger_manual_improvement(self):
        """Manually trigger an improvement cycle"""
        if not self.enable_self_improvement:
            self.log.warning("Self-improvement is not enabled")
            return
        
        await self._perform_self_improvement_cycle()
    
    def get_improvement_status(self) -> dict:
        """Get current status of self-improvement system"""
        if not self.enable_self_improvement:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "interaction_count": self.interaction_count,
            "last_reflection_time": self.last_reflection_time.isoformat(),
            "improvement_task_running": self.improvement_task and not self.improvement_task.done()
        }