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

# C - function definitions, structs, enums, unions, typedefs, macros, includes, calls
C_QUERIES = """
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @definition.function

(function_definition
  declarator: (pointer_declarator
    declarator: (function_declarator
      declarator: (identifier) @name))) @definition.function

(struct_specifier
  name: (type_identifier) @name) @definition.struct

(enum_specifier
  name: (type_identifier) @name) @definition.enum

(union_specifier
  name: (type_identifier) @name) @definition.union

(type_definition
  declarator: (type_identifier) @name) @definition.typedef

(preproc_def
  name: (identifier) @name) @definition.macro

(preproc_include
  path: (_) @import.source) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (field_expression
    field: (field_identifier) @call.name)) @call
"""

# C++ - extends C with classes, namespaces, methods
CPP_QUERIES = """
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @definition.function

(function_definition
  declarator: (function_declarator
    declarator: (qualified_identifier
      name: (identifier) @name))) @definition.method

(function_definition
  declarator: (pointer_declarator
    declarator: (function_declarator
      declarator: (identifier) @name))) @definition.function

(class_specifier
  name: (type_identifier) @name) @definition.class

(struct_specifier
  name: (type_identifier) @name) @definition.struct

(enum_specifier
  name: (type_identifier) @name) @definition.enum

(union_specifier
  name: (type_identifier) @name) @definition.union

(namespace_definition
  name: (namespace_identifier) @name) @definition.namespace

(type_definition
  declarator: (type_identifier) @name) @definition.typedef

(preproc_def
  name: (identifier) @name) @definition.macro

(preproc_include
  path: (_) @import.source) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (field_expression
    field: (field_identifier) @call.name)) @call

(call_expression
  function: (qualified_identifier
    name: (identifier) @call.name)) @call

; Heritage: class Derived : public Base
(class_specifier
  name: (type_identifier) @heritage.class
  (base_class_clause
    (type_identifier) @heritage.extends)) @heritage
"""

# JavaScript - functions, classes, methods, arrow functions, imports, calls, heritage
JS_QUERIES = """
(function_declaration
  name: (identifier) @name) @definition.function

(class_declaration
  name: (identifier) @name) @definition.class

(method_definition
  name: (property_identifier) @name) @definition.method

(variable_declarator
  name: (identifier) @name
  value: (arrow_function)) @definition.function

(import_statement
  source: (string) @import.source) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (member_expression
    property: (property_identifier) @call.name)) @call

; require("module")
(call_expression
  function: (identifier) @import.require
  arguments: (arguments (string) @import.source)) @import

; Heritage: class Foo extends Bar
(class_declaration
  name: (identifier) @heritage.class
  (class_heritage
    (identifier) @heritage.extends)) @heritage
"""

# TypeScript - extends JS with interfaces, enums, type aliases, implements
TS_QUERIES = """
(function_declaration
  name: (identifier) @name) @definition.function

(class_declaration
  name: (type_identifier) @name) @definition.class

(method_definition
  name: (property_identifier) @name) @definition.method

(variable_declarator
  name: (identifier) @name
  value: (arrow_function)) @definition.function

(interface_declaration
  name: (type_identifier) @name) @definition.interface

(enum_declaration
  name: (identifier) @name) @definition.enum

(type_alias_declaration
  name: (type_identifier) @name) @definition.type_alias

(import_statement
  source: (string) @import.source) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (member_expression
    property: (property_identifier) @call.name)) @call

; Heritage: class Foo extends Bar
(class_declaration
  name: (type_identifier) @heritage.class
  (class_heritage
    (extends_clause
      value: (identifier) @heritage.extends))) @heritage

; Heritage: class Foo implements Bar
(class_declaration
  name: (type_identifier) @heritage.class
  (class_heritage
    (implements_clause
      (type_identifier) @heritage.implements))) @heritage.impl
"""

# Go - functions, methods, type declarations, imports, calls
GO_QUERIES = """
(function_declaration
  name: (identifier) @name) @definition.function

(method_declaration
  name: (field_identifier) @name) @definition.method

(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (struct_type))) @definition.struct

(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (interface_type))) @definition.interface

(import_declaration
  (import_spec
    path: (interpreted_string_literal) @import.source)) @import

(import_declaration
  (import_spec_list
    (import_spec
      path: (interpreted_string_literal) @import.source))) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (selector_expression
    field: (field_identifier) @call.name)) @call
"""

# Rust - functions, structs, enums, traits, impl, type aliases, use, calls
RUST_QUERIES = """
(function_item
  name: (identifier) @name) @definition.function

(struct_item
  name: (type_identifier) @name) @definition.struct

(enum_item
  name: (type_identifier) @name) @definition.enum

(trait_item
  name: (type_identifier) @name) @definition.trait

(impl_item
  type: (type_identifier) @name) @definition.impl

(type_item
  name: (type_identifier) @name) @definition.type_alias

(use_declaration
  argument: (_) @import.source) @import

(call_expression
  function: (identifier) @call.name) @call

(call_expression
  function: (field_expression
    field: (field_identifier) @call.name)) @call

(call_expression
  function: (scoped_identifier
    name: (identifier) @call.name)) @call

; Heritage: impl Trait for Struct
(impl_item
  trait: (type_identifier) @heritage.extends
  type: (type_identifier) @heritage.class) @heritage
"""

LANGUAGE_QUERIES: dict[str, str] = {
    "python": PYTHON_QUERIES,
    "java": JAVA_QUERIES,
    "lua": LUA_QUERIES,
    "c": C_QUERIES,
    "cpp": CPP_QUERIES,
    "javascript": JS_QUERIES,
    "typescript": TS_QUERIES,
    "go": GO_QUERIES,
    "rust": RUST_QUERIES,
}
