from typing import Any
import json
import re
import ast

def parse_llm_json_response(content: Any) -> dict:
    if not isinstance(content, str):
        if isinstance(content, dict):
            return content
        return {"error": "입력이 문자열이 아닙니다."}
    
    if not content.strip():
        return {"error": "빈 응답입니다."}

    # 1. 마크다운 ```json ``` 블럭 추출
    md_json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    md_match = re.search(md_json_pattern, content)
    if md_match:
        content = md_match.group(1).strip()

    # 2. 중괄호로 시작하는 JSON 텍스트 추출 (이스케이프 포함 가능)
    json_pattern = r'(\{[\s\S]*\})'
    json_match = re.search(json_pattern, content)
    if json_match:
        content = json_match.group(1).strip()

    # 3. 이스케이프 문자열 처리 우선 시도 (ex: \n, \", \t 등)
    if '\\n' in content or '\\"' in content or '\\\\' in content:
        try:
            evaluated = ast.literal_eval(f'"""{content}"""')
            return json.loads(evaluated)
        except (SyntaxError, ValueError, json.JSONDecodeError) as e:
            pass

    # 4. 일반 JSON 파싱 시도
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        return {
            "error": f"JSON 파싱 실패: {str(e)}",
            "original_content": content
        }
