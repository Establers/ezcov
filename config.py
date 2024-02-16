def format_config (config, indent=0) :
    """
    yaml 파일을 예쁘게 출력하기 위한 함수
    """
    lines = []
    for key, value in config.items() :
        prefix = " " * indent
        if isinstance(value, dict) : 
            lines.append(f"{prefix}{key}")
            lines.append(format_config(value, indent + 1))

        else : 
            lines.append(f"{prefix}{key} : {value}")
    
    return "\n".join(lines)


