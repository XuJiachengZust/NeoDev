# Queries aligned with gitnexus/src/core/ingestion/tree-sitter-queries.ts
# Capture names: @name, @definition.class, @definition.function, @import.source, @call.name, @heritage.class, @heritage.extends

PYTHON_QUERIES = """
(class_definition
  name: (identifier) @name) @definition.class

(function_definition
  name: (identifier) @name) @definition.function

(import_statement
  name: (dotted_name) @import.source) @import

(import_from_statement
  module_name: (dotted_name) @import.source) @import

(call
  function: (identifier) @call.name) @call

(call
  function: (attribute
    attribute: (identifier) @call.name)) @call

; Heritage queries - Python class inheritance
(class_definition
  name: (identifier) @heritage.class
  superclasses: (argument_list
    (identifier) @heritage.extends)) @heritage
"""

# Java - aligned with tree-sitter-queries.ts JAVA_QUERIES
JAVA_QUERIES = """
(class_declaration name: (identifier) @name) @definition.class
(interface_declaration name: (identifier) @name) @definition.interface
(enum_declaration name: (identifier) @name) @definition.enum
(annotation_type_declaration name: (identifier) @name) @definition.annotation
(method_declaration name: (identifier) @name) @definition.method
(constructor_declaration name: (identifier) @name) @definition.constructor
(import_declaration (_) @import.source) @import
(method_invocation name: (identifier) @call.name) @call
(method_invocation object: (_) name: (identifier) @call.name) @call
(class_declaration name: (identifier) @heritage.class
  (superclass (type_identifier) @heritage.extends)) @heritage
(class_declaration name: (identifier) @heritage.class
  (super_interfaces (type_list (type_identifier) @heritage.implements))) @heritage.impl
"""

# Lua (tree-sitter-lua): function_declaration, require() as import, function calls
LUA_QUERIES = """
; function name() end and local function name() end
(function_declaration
  (identifier) @name) @definition.function

; function table.field() end
(function_declaration
  name: (dot_index_expression
    table: (identifier) @module.name
    field: (identifier) @name) @function.full) @definition.function

; function obj:method() end
(function_declaration
  name: (method_index_expression
    table: (identifier) @module.name
    method: (identifier) @name) @function.full) @definition.function

; require("module") -> import
(function_call
  (identifier) @import.require
  (arguments (string) @import.source)) @import

; function call: name()
(function_call
  (identifier) @call.name) @call

; method call: obj:method() - method_index_expression has "method" field
(function_call
  name: (method_index_expression
    method: (identifier) @call.name)) @call
"""

LANGUAGE_QUERIES: dict[str, str] = {
    "python": PYTHON_QUERIES,
    "java": JAVA_QUERIES,
    "lua": LUA_QUERIES,
}
