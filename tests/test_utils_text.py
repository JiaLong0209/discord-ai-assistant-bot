import pytest
from utils.text import remove_chinese_sentences, remove_parentheses

def test_remove_parentheses():
    text = "これはテスト(注釈)です。"
    assert remove_parentheses(text) == "これはテストです。"

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("これは日本語。這是中文句子。次の日本語！", "これは日本語。 次の日本語！"),
        (
            "ええと…変なこと言ってるっピ？(・・;) 薯大大のことばっかり話してると、頭がポヨポヨになっちゃうかもっピよ！(><) 翻譯：欸欸…在說什麼奇怪的話嗶？(・・;) 一直說薯大大，頭可能會變得糊糊的嗶喔！(><)",
            "ええと…変なこと言ってるっピ？ 薯大大のことばっかり話してると、頭がポヨポヨになっちゃうかもっピよ！"
        ),
    ]
)

def test_remove_chinese_sentences(input_text, expected):
    assert remove_chinese_sentences(input_text) == expected
