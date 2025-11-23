"""
IBM watsonx Orchestrate Flow execution engine.
Executes flows defined in JSON, invoking skills and running local logic.
"""
from typing import Optional, Dict, Any, List
import json
import os
from app.config import Config
from app.logger import get_logger
from .skills import orchestrate_skills

logger = get_logger(__name__)


class FlowRunner:
    """Orchestrate flow execution engine"""
    
    def __init__(self):
        self.flows: Dict[str, Dict[str, Any]] = {}
        self._load_flows()
        
        # Map script names to methods
        self.script_handlers = {
            "validate_invoice": self._script_validate_invoice,
            "auto_approve": self._script_auto_approve
        }
    
    def _load_flows(self):
        """Load flow definitions"""
        try:
            flow_path = os.path.join("orchestrate", "invoice_processing_flow.json")
            if os.path.exists(flow_path):
                with open(flow_path, "r") as f:
                    flow = json.load(f)
                    self.flows[flow.get("name", "InvoiceProcessingFlow")] = flow
                    logger.info(f"Loaded flow: {flow.get('name')}")
            else:
                logger.warning(f"Flow definition not found at {flow_path}")
        except Exception as e:
            logger.error(f"Failed to load flows: {str(e)}")
    
    def execute_flow(self, flow_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an Orchestrate flow"""
        if flow_name not in self.flows:
            return {"error": f"Flow {flow_name} not found", "status": "failed"}
        
        flow = self.flows[flow_name]
        steps = flow.get("steps", [])
        
        context = input_data.copy()
        results = []
        
        logger.info(f"Starting flow execution: {flow_name}")
        
        try:
            self._execute_steps(steps, context, results)
            status = "completed"
        except Exception as e:
            logger.error(f"Flow execution failed: {str(e)}")
            status = "failed"
            results.append({"error": str(e)})
            
        return {
            "flow": flow_name,
            "status": status,
            "results": results,
            "final_context": context
        }

    def _execute_steps(self, steps: List[Dict[str, Any]], context: Dict[str, Any], results: List[Dict[str, Any]]):
        """Execute a list of steps"""
        for step in steps:
            step_id = step.get("id")
            step_type = step.get("type")
            
            logger.debug(f"Executing step: {step_id} ({step_type})")
            
            if step_type == "skill":
                self._execute_skill_step(step, context, results)
            
            elif step_type == "script":
                self._execute_script_step(step, context, results)
            
            elif step_type == "switch":
                self._execute_switch_step(step, context, results)
                
            elif step_type == "wait_for_event":
                # For synchronous execution, we can't really wait. 
                # We'll just log it and stop.
                logger.info(f"Flow paused waiting for event: {step.get('event')}")
                results.append({"step": step_id, "status": "paused", "reason": "wait_for_event"})
                break

    def _execute_skill_step(self, step: Dict[str, Any], context: Dict[str, Any], results: List[Dict[str, Any]]):
        """Execute a skill step"""
        skill_name = step.get("skill")
        skill_input = step.get("input", {})
        
        # Resolve variables
        resolved_input = self._resolve_variables(skill_input, context)
        
        # Invoke skill
        result = orchestrate_skills.invoke_skill(skill_name, resolved_input)
        
        # Store output
        output_var = step.get("output", step.get("id"))
        if result:
            context[output_var] = result
            results.append({"step": step.get("id"), "status": "success", "output": result})
        else:
            results.append({"step": step.get("id"), "status": "failed"})

    def _execute_script_step(self, step: Dict[str, Any], context: Dict[str, Any], results: List[Dict[str, Any]]):
        """Execute a script step"""
        script_content = step.get("script", "")
        
        # Simple heuristic to find handler
        handler = None
        for name, method in self.script_handlers.items():
            if name in script_content:
                handler = method
                break
        
        if handler:
            try:
                result = handler(context)
                output_var = step.get("output", step.get("id"))
                context[output_var] = result
                results.append({"step": step.get("id"), "status": "success", "output": result})
            except Exception as e:
                logger.error(f"Script execution failed: {str(e)}")
                results.append({"step": step.get("id"), "status": "failed", "error": str(e)})
        else:
            logger.warning(f"No handler found for script: {script_content}")
            results.append({"step": step.get("id"), "status": "skipped", "reason": "no_handler"})

    def _execute_switch_step(self, step: Dict[str, Any], context: Dict[str, Any], results: List[Dict[str, Any]]):
        """Execute a switch step"""
        cases = step.get("cases", [])
        matched = False
        
        for case in cases:
            condition = case.get("condition")
            if condition == "else" or self._evaluate_condition(condition, context):
                logger.info(f"Switch case matched: {condition}")
                self._execute_steps(case.get("actions", []), context, results)
                matched = True
                break
        
        if not matched:
            logger.info("No switch cases matched")

    def _resolve_variables(self, template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve variables in template using context"""
        resolved = {}
        for key, value in template.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                # Simple replacement for now
                for ctx_key, ctx_val in context.items():
                    if isinstance(ctx_val, (str, int, float, bool)):
                         value = value.replace(f"{{{{{ctx_key}}}}}", str(ctx_val))
                    # Handle nested object access like {{invoice.id}} - simplified
                    if isinstance(ctx_val, dict):
                        for sub_key, sub_val in ctx_val.items():
                             value = value.replace(f"{{{{{ctx_key}.{sub_key}}}}}", str(sub_val))
                resolved[key] = value
            else:
                resolved[key] = value
        return resolved
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition string"""
        try:
            # Very basic evaluation logic for the hackathon
            # Supports: risk.score < 0.3 && validation.ok == true
            
            # 1. Resolve variables
            eval_str = condition
            
            # Helper to get nested value
            def get_val(path):
                parts = path.split('.')
                val = context
                for p in parts:
                    if isinstance(val, dict):
                        val = val.get(p)
                    else:
                        return None
                return val

            # Replace known variables in condition string
            # This is fragile but works for the specific flow we have
            if "risk.score" in eval_str:
                score = get_val("risk.score") or get_val("risk.result.score") or 0.5
                eval_str = eval_str.replace("risk.score", str(score))
                
            if "validation.ok" in eval_str:
                val_ok = get_val("validation.ok")
                # Python bool is True/False, JS is true/false
                eval_str = eval_str.replace("validation.ok", str(val_ok)).replace("true", "True").replace("false", "False")
            
            # Replace JS operators with Python operators
            eval_str = eval_str.replace("&&", " and ").replace("||", " or ")
            
            # 2. Eval
            return eval(eval_str)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {condition} - {str(e)}")
            return False

    # Script Handlers
    def _script_validate_invoice(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate invoice logic"""
        invoice = context.get("invoice", {})
        # Simple validation rules
        if invoice.get("total", 0) > 0 and invoice.get("vendor"):
            return {"ok": True, "message": "Valid"}
        return {"ok": False, "message": "Missing required fields"}

    def _script_auto_approve(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-approve logic"""
        invoice = context.get("invoice", {})
        logger.info(f"Auto-approving invoice: {invoice.get('invoice_id')}")
        return {"approved": True}


# Global flow runner instance
flow_runner = FlowRunner()
