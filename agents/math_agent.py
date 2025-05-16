"""
Math agent implementation.
"""

import time
import re
from python_a2a import AgentCard, AgentSkill, Message, TextContent, MessageRole, Task, TaskStatus, TaskState
from config import logger
from agents.base_agent import BaseAgent

class MathAgent(BaseAgent):
    """Agent that solves mathematical problems and calculations."""
    
    def __init__(self):
        """Initialize the math agent with its capabilities."""
        agent_card = AgentCard(
            name="Math Agent",
            description="Performs mathematical calculations and solves math problems",
            url="http://localhost:0",  # Will be updated when server starts
            version="1.0.0",
            skills=[
                AgentSkill(
                    name="Basic Arithmetic",
                    description="Perform basic arithmetic operations like addition, subtraction, multiplication, and division",
                    tags=["math", "arithmetic", "calculate", "add", "subtract", "multiply", "divide"],
                    examples=["What is 24 * 7?", "Calculate 156 / 12"]
                ),
                AgentSkill(
                    name="Advanced Math",
                    description="Solve more complex math problems including algebra and equations",
                    tags=["math", "algebra", "equation", "solve", "evaluate", "expression"],
                    examples=["Solve the equation 3x + 7 = 22", "What is the value of x in 2x - 5 = 11?"]
                )
            ]
        )
        super().__init__(agent_card=agent_card)
    
    def handle_message(self, message: Message) -> Message:
        """Handle incoming message with a math request."""
        query = message.content.text if hasattr(message.content, "text") else ""
        
        # Add a small delay to simulate processing
        logger.info("[Math Agent] Calculating answer...")
        time.sleep(0.3)
        
        answer = self._solve_math_problem(query)
        
        logger.info("[Math Agent] Calculation complete")
        
        return Message(
            content=TextContent(text=answer),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id
        )
    
    def handle_task(self, task: Task) -> Task:
        """Handle task-based math request."""
        query = self._extract_query_from_task(task)
        
        # Add a small delay to simulate processing
        logger.info("[Math Agent] Calculating answer...")
        time.sleep(0.3)
        
        answer = self._solve_math_problem(query)
        
        logger.info("[Math Agent] Calculation complete")
        
        # Update task with the calculation result
        task.artifacts = [{
            "parts": [{"type": "text", "text": answer}]
        }]
        task.status = TaskStatus(state=TaskState.COMPLETED)
        return task
    
    def _solve_math_problem(self, query: str) -> str:
        """
        Solve a mathematical problem from the query.
        
        Args:
            query: The math problem to solve
            
        Returns:
            The solution as a string
        """
        query_lower = query.lower()
        
        # Check for basic arithmetic operations directly in the query
        # Pattern to match simple arithmetic expressions
        basic_arithmetic_pattern = r'(\d+(\.\d+)?)\s*([\+\-\*\/\^])\s*(\d+(\.\d+)?)'
        match = re.search(basic_arithmetic_pattern, query)
        
        if match:
            try:
                # Extract the numbers and operator
                num1 = float(match.group(1))
                operator = match.group(3)
                num2 = float(match.group(4))
                
                # Perform the calculation
                result = None
                if operator == '+':
                    result = num1 + num2
                elif operator == '-':
                    result = num1 - num2
                elif operator == '*':
                    result = num1 * num2
                elif operator == '/':
                    if num2 == 0:
                        return "Error: Division by zero is not allowed."
                    result = num1 / num2
                elif operator == '^':
                    result = num1 ** num2
                
                # Format the result (display as integer if it's a whole number)
                if result is not None:
                    if result.is_integer():
                        return f"The result of {num1} {operator} {num2} is {int(result)}"
                    else:
                        return f"The result of {num1} {operator} {num2} is {result}"
            except Exception as e:
                logger.error(f"Error in calculation: {e}")
        
        # Check for equation solving
        equation_pattern = r'(\d*x)\s*([\+\-])\s*(\d+)\s*=\s*(\d+)'
        match = re.search(equation_pattern, query)
        
        if match:
            try:
                # Extract the components
                x_term = match.group(1)
                operator = match.group(2)
                constant1 = int(match.group(3))
                constant2 = int(match.group(4))
                
                # Get the coefficient of x
                if x_term == 'x':
                    coefficient = 1
                else:
                    coefficient = int(x_term[:-1])
                
                # Solve the equation
                if operator == '+':
                    # ax + b = c -> x = (c - b) / a
                    x_value = (constant2 - constant1) / coefficient
                else:  # operator == '-'
                    # ax - b = c -> x = (c + b) / a
                    x_value = (constant2 + constant1) / coefficient
                
                # Format the result
                if x_value.is_integer():
                    return f"Solving the equation {x_term} {operator} {constant1} = {constant2}:\nx = {int(x_value)}"
                else:
                    return f"Solving the equation {x_term} {operator} {constant1} = {constant2}:\nx = {x_value}"
            except Exception as e:
                logger.error(f"Error solving equation: {e}")
        
        # Handle special math keywords
        if "square root" in query_lower:
            # Try to extract a number after "square root"
            sqrt_pattern = r'square root of (\d+(\.\d+)?)'
            match = re.search(sqrt_pattern, query_lower)
            if match:
                try:
                    num = float(match.group(1))
                    result = num ** 0.5
                    if result.is_integer():
                        return f"The square root of {num} is {int(result)}"
                    else:
                        return f"The square root of {num} is {result}"
                except Exception as e:
                    logger.error(f"Error calculating square root: {e}")
        
        # If no patterns matched or calculation failed
        return "I couldn't understand or solve the mathematical problem. Please provide a clearer expression or equation." 