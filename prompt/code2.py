table = str.maketrans("", "", "#*|")

def main(s: str):
    return {
        "result": s.translate(table)
    }