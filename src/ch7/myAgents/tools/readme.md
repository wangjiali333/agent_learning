工具架构:

ToolParameter
     ↓
   Tool
     ↓
FunctionTool
     ↓
ToolRegistry:  容器
     ↓
 ┌─────────────┬──────────────┐
 ↓             ↓              ↓
Prompt       Function       Future MCP
Agent        Calling


1. 基于Prompt-base Agent的工具调用的 schema 格式
   [{ 工具名: 工具描述 } ]


2.  OpenAI function calling schema 格式
        schema格式如下:
        tools
        └── tool
            ├── type
            └── function
                ├── name
                ├── description
                └── parameters
                        ├── type
                        ├── properties
                        └── required

        用于 FunctionCallAgent，使工具能够被 OpenAI 原生 function calling 使用

3. MCP schema 格式
  {
  "name": "calculator",
  "description": "执行数学计算",
  "inputSchema": {
    "type": "object",
    "properties": {
      "expression": {
        "type": "string",
        "description": "需要计算的数学表达式"
      }
    },
    "required": ["expression"]
  }
}

