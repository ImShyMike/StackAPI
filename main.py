"""Code for the most useful API ever made"""

import array
import logging
import secrets
import time
from functools import wraps

from flasgger import Swagger
from flask import Flask, request

HOST = "0.0.0.0"
PORT = 2000

MAX_STACK_SIZE = 1024 * 100
MAX_STACKS = 1000

app = Flask(__name__)

app.config["SWAGGER"] = {
    "title": "Stack API",
    "description": "The most useful API ever made",
    "version": "1.0.0",
    "uiversion": 3,
    "termsOfService": "",
    "specs": [
        {
            "endpoint": "api",
            "route": "/apidocs.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "specs_route": "/apidocs/"
}
swagger = Swagger(app)

app.stacks = {}

logger = logging.getLogger("werkzeug")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("error.log")
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def refresh_stack_expiry(stack_id: int):
    """Refresh the expiry of a stack"""
    app.stacks[stack_id]["expiry"] = time.time() + 60 * 60  # 1 hour


def remove_expired_stacks():
    """Remove expired stacks"""
    for stack_id, stack in list(app.stacks.items()):
        if stack["expiry"] < time.time():
            del app.stacks[stack_id]


def require_valid_stack_id():
    """Decorator to require a valid stack ID"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                stack_id = int(request.args.get("id"))
            except (TypeError, ValueError):
                return "Stack ID must be an integer", 400

            if stack_id not in app.stacks:
                return "Stack not found", 404

            refresh_stack_expiry(stack_id)

            return func(stack_id, *args, **kwargs)

        return wrapper

    return decorator


@app.route("/")
def home():
    """
    Simple way to check if the app is running
    ---
    produces: ["text/plain"]
    responses:
      200:
        description: API is working
        examples:
          text/plain: API is working
    """
    return "API is working"


@app.route("/api/create", methods=["POST"])
def create():
    """
    Create a new stack
    ---
    produces: ["text/plain"]
    responses:
      201:
        description: Stack created successfully
        schema:
          type: string
          example: "123456789"
      400:
        description: Maximum number of stacks reached
        schema:
          type: string
          example: "Maximum number of stacks reached (1000)"
    """
    if len(app.stacks) >= MAX_STACKS:
        return f"Maximum number of stacks reached ({MAX_STACKS})", 400

    stack_id = int(secrets.token_hex(8), 16)
    expiry = time.time() + 60 * 60  # 1 hour
    app.stacks[stack_id] = {
        "array": array.array("q"),
        "expiry": expiry,
    }

    return str(stack_id), 201


@app.route("/api/push", methods=["POST"])
@require_valid_stack_id()
def push(stack_id: int):
    """
    Push a value to the stack
    ---
    produces: ["text/plain"]
    parameters:
      - name: id
        in: query
        type: integer
        required: true
        description: Stack ID
      - name: value
        in: query
        type: integer
        required: true
        description: Value to push to the stack
    responses:
      200:
        description: Value pushed successfully
        examples:
          text/plain: Ok
      400:
        description: Error pushing value
        schema:
          type: string
          enum: ["Value must be an integer", "Value is too large", "Stack overflow"]
      404:
        description: Stack not found
    """
    try:
        value = int(request.args.get("value"))
    except (TypeError, ValueError):
        return "Value must be an integer", 400

    stack = app.stacks[stack_id]["array"]

    try:
        stack.append(value)
    except OverflowError:
        return "Value is too large", 400

    if stack.buffer_info()[1] > MAX_STACK_SIZE:
        stack.pop()

        return "Stack overflow", 400

    return "Ok", 200


@app.route("/api/push_bulk", methods=["POST"])
@require_valid_stack_id()
def push_bulk(stack_id: int):
    """
    Push multiple values to the stack
    ---
    produces: ["text/plain"]
    parameters:
      - name: id
        in: query
        type: integer
        required: true
        description: Stack ID
      - name: values
        in: query
        type: string
        required: true
        description: Comma-separated list of integers
        example: "1,2,3,4,5"
    responses:
      200:
        description: Values pushed successfully
        examples:
          text/plain: Ok
      400:
        description: Error pushing values
        schema:
          type: string
          enum: ["Values must be provided", "All values must be integers", "Value is too large", "Stack overflow"]
      404:
        description: Stack not found
    """
    values = request.args.get("values")
    if not values:
        return "Values must be provided", 400
    try:
        values = values.split(",")
        values = [int(value) for value in values]
    except (TypeError, ValueError):
        return "All values must be integers", 400

    stack = app.stacks[stack_id]["array"]

    for value in values:
        try:
            stack.append(value)
        except OverflowError:
            return "Value is too large", 400

        if stack.buffer_info()[1] > MAX_STACK_SIZE:
            stack.pop()

            return "Stack overflow", 400

    return "Ok", 200


@app.route("/api/pop", methods=["POST"])
@require_valid_stack_id()
def pop(stack_id: int):
    """
    Pop a value from the stack
    ---
    produces: ["text/plain"]
    parameters:
      - name: id
        in: query
        type: integer
        required: true
        description: Stack ID
    responses:
      200:
        description: Value popped successfully
        schema:
          type: string
          example: "42"
      400:
        description: Stack underflow
        examples:
          text/plain: Stack underflow
      404:
        description: Stack not found
    """
    stack = app.stacks[stack_id]["array"]

    if len(stack) <= 0:
        return "Stack underflow", 400

    return str(stack.pop()), 200


@app.route("/api/pop_bulk", methods=["POST"])
@require_valid_stack_id()
def pop_bulk(stack_id: int):
    """
    Pop multiple values from the stack
    ---
    produces: ["text/plain"]
    parameters:
      - name: id
        in: query
        type: integer
        required: true
        description: Stack ID
      - name: count
        in: query
        type: integer
        required: true
        description: Number of values to pop
    responses:
      200:
        description: Values popped successfully
        schema:
          type: string
          example: "5,4,3,2,1"
      400:
        description: Error popping values
        schema:
          type: string
          enum: ["Count must be an integer", "Stack underflow"]
      404:
        description: Stack not found
    """
    try:
        count = int(request.args.get("count"))
    except (TypeError, ValueError):
        return "Count must be an integer", 400

    stack = app.stacks[stack_id]["array"]

    if len(stack) < count:
        return "Stack underflow", 400

    return str(",".join([str(stack.pop()) for _ in range(count)])), 200


@app.route("/api/size", methods=["GET"])
@require_valid_stack_id()
def size(stack_id: int):
    """
    Get the size of a stack
    ---
    produces: ["text/plain"]
    parameters:
      - name: id
        in: query
        type: integer
        required: true
        description: Stack ID
    responses:
      200:
        description: Stack size
        schema:
          type: string
          example: "5"
      404:
        description: Stack not found
    """
    return str(app.stacks[stack_id]["array"].buffer_info()[1]), 200


@app.route("/api/peek", methods=["GET"])
@require_valid_stack_id()
def peek(stack_id: int):
    """
    Peek the top value of a stack
    ---
    produces: ["text/plain"]
    parameters:
      - name: id
        in: query
        type: integer
        required: true
        description: Stack ID
    responses:
      200:
        description: Top value of the stack
        schema:
          type: string
          example: "42"
      400:
        description: Stack is empty
        examples:
          text/plain: Stack is empty
      404:
        description: Stack not found
    """
    stack = app.stacks[stack_id]["array"]

    if len(stack) == 0:
        return "Stack is empty", 400

    return str(stack[-1]), 200


@app.route("/api/destroy", methods=["DELETE"])
@require_valid_stack_id()
def destroy(stack_id: int):
    """
    Destroy a stack
    ---
    produces: ["text/plain"]
    parameters:
      - name: id
        in: query
        type: integer
        required: true
        description: Stack ID
    responses:
      200:
        description: Stack destroyed successfully
        examples:
          text/plain: Ok
      404:
        description: Stack not found
    """
    del app.stacks[stack_id]

    return "Ok", 200


@app.route("/api/list", methods=["GET"])
def list_stacks():
    """List all stacks
---
produces: ["text/plain"]
responses:
  200:
    description: List of stacks
    schema:
      type: string
      example: "2/1000 stacks\\n\\nStack list:\\n0: 5/102400 (0%)\\n1: 10/102400 (0%)"
    """
    stack_count = len(app.stacks)
    data = ""
    for i, stack in enumerate(app.stacks.values()):
        array_size = stack["array"].buffer_info()[1]
        data += (
            f"{i}: {array_size}/{MAX_STACK_SIZE} "
            f"({round(array_size / MAX_STACK_SIZE * 100)}%)\n"
        )
    return f"{stack_count}/{MAX_STACKS} stacks\n\nStack list:\n{data[:-1]}", 200


@app.before_request
def before_request():
    """Remove expired stacks before each request"""
    remove_expired_stacks()


@app.after_request
def set_plain_text(response):
    """Set the response content type to plain text for all requests (except for Swagger)"""
    if not request.path.startswith("/apidocs") and not request.path.startswith(
        "/flasgger_static"
    ):
        response.headers["Content-Type"] = "text/plain"
    return response


if __name__ == "__main__":
    app.run(HOST, port=PORT, use_reloader=False, debug=False)
