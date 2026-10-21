import json
import os
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from pypdf import PdfReader

# 페이지 기본 설정
st.set_page_config(
    page_title="규은핑의 문제 생성기", page_icon="📚", layout="centered"
)

st.title("📚 규은핑의 문제 생성기!!")
st.write(
    "PDF를 업로드하면 준피티가 문제를 만듭니다. 대기할 동안 주니 생각을 해주세요..!"
)

# banner.png가 실제로 있을 때만 이미지를 띄워 에러 방지
if os.path.exists("banner.png"):
  st.image("banner.png", use_container_width=True)

# Streamlit Secrets에 키가 등록되어 있는지 확인 후 자동 로드
if "GEMINI_API_KEY" in st.secrets:
  api_key = st.secrets["GEMINI_API_KEY"]
else:
  with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown(
        "[Google AI Studio에서 API 키 발급받기](https://aistudio.google.com/)"
    )
    st.info(
        "발급받은 Gemini API Key를 입력하면 앱을 정상적으로 사용할 수 있습니다."
    )

# PDF 파일 여러 개 업로드 가능하도록 설정 (accept_multiple_files=True)
uploaded_files = st.file_uploader(
    "공부할 PDF 강의 자료들을 업로드하세요 (여러 개 선택 가능)",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files and api_key:
  client = genai.Client(api_key=api_key)

  # 업로드된 모든 파일의 이름을 조합하여 변경 감지 및 텍스트 통합 추출
  file_names = tuple(f.name for f in uploaded_files)
  if "pdf_text" not in st.session_state or st.session_state.get("uploaded_filenames") != file_names:
    with st.spinner("📄 PDF 파일들 분석 중..."):
      try:
        combined_text = ""
        for uploaded_file in uploaded_files:
          reader = PdfReader(uploaded_file)
          for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
              combined_text += extracted + "\n"
        st.session_state["pdf_text"] = combined_text
        st.session_state["uploaded_filenames"] = file_names
      except Exception as e:
        st.error(f"PDF를 읽는 중 오류가 발생했습니다: {e}")
        st.session_state["pdf_text"] = ""

  text = st.session_state.get("pdf_text", "")

  # PDF에서 글자가 읽히지 않았을 때 안내
  if not text.strip():
    st.warning("⚠️ PDF 파일에서 텍스트를 추출하지 못했습니다. 스캔된 이미지 PDF인지 확인해 주세요.")


  # 문제 생성 함수 (기본 20문제로 설정)
  def generate_questions(num_count=20):
    with st.spinner(f"🤖 준피티가 20문제를 출제하고 있습니다..."):
      limited_text = text[:6000] if text else "강의 자료 내용을 기반으로 문제를 출제해 주세요."

      prompt = f"""
            다음 강의 텍스트들을 바탕으로 핵심을 파악할 수 있는 객관식 문제 {num_count}개를 만들어주세요.
            반드시 아래 JSON 형식으로만 응답해주세요. 마크다운 백틱(```json ... ```)을 쓰지 말고 순수 JSON 문자열만 반환해주세요.
            
            [
              {{
                "question": "문제 내용",
                "options": ["1번 보기", "2번 보기", "3번 보기", "4번 보기"],
                "answer": 정답번호(1부터 4까지의 정수),
                "explanation": "상세한 해설 내용"
              }}
            ]
            
            강의 텍스트:
            {limited_text}
            """
      try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        res_text = response.text.strip()

        # 마크다운 태그 정제
        if res_text.startswith("```json"):
          res_text = res_text[7:]
        if res_text.startswith("```"):
          res_text = res_text[3:]
        if res_text.endswith("```"):
          res_text = res_text[:-3]

        new_questions = json.loads(res_text.strip())
        if "questions" not in st.session_state:
          st.session_state["questions"] = []
        st.session_state["questions"].extend(new_questions)
        st.success(f"✨ {len(new_questions)}개의 문제가 빠르게 생성되었습니다!")
        return True
      except Exception as e:
        st.session_state["error_msg"] = str(e)
        return False


  # 최초 문제 생성 버튼 (20문제)
  if "questions" not in st.session_state:
    if st.button("🚀 준피티에게 문제 생성 요청하기 (20문제 다 맞으면 선물!)"):
      if generate_questions(20):
        st.rerun()

  # 에러 메시지 출력
  if "error_msg" in st.session_state:
    st.error(
        f"❌ AI 문제 생성 중 오류가 발생했습니다:\n\n"
        f"{st.session_state['error_msg']}"
    )

# 문제가 생성된 경우 화면에 표시
if "questions" in st.session_state and st.session_state["questions"]:
  st.markdown("---")
  st.subheader(f"📝 문제 풀기 (총 {len(st.session_state['questions'])}문제)")

  user_answers = {}
  for i, q in enumerate(st.session_state["questions"]):
    st.markdown(f"**문제 {i+1}. {q['question']}**")
    user_answers[i] = st.radio(
        f"보기 선택 ({i+1})", q["options"], key=f"q_{i}", index=None
    )
    st.write("")

  if st.button("📊 제출 및 채점하기"):
    score = 0
    wrong_list = []
    st.markdown("---")
    st.subheader("🎯두구두구 채점 결과")

    for i, q in enumerate(st.session_state["questions"]):
      selected = user_answers.get(i)
      correct_option = q["options"][q["answer"] - 1]

      if selected == correct_option:
        score += 1
        st.success(f"문제 {i+1} 사랑해! 🎉\n\n> **해설**: {q['explanation']}")
      elif selected:
        st.error(
            f"문제 {i+1} 시러해... (선택한 답: {selected} / 정답:"
            f" '{correct_option}')\n\n> **해설**: {q['explanation']}"
        )
        wrong_list.append(q)  # 오답 노트용 수집
      else:
        st.warning(
            f"문제 {i+1}을 풀지 않았습니다. (정답: '{correct_option}')\n\n> "
            f"**해설**: {q['explanation']}"
        )
        wrong_list.append(q)  # 안 푼 것도 오답 노트에 포함

    total_len = len(st.session_state["questions"])
    ratio = score / total_len

    # [칭호 시스템] 점수 비율별 칭호 부여
    if ratio == 1.0:
      user_title = "🏆 규은핑! 준피티 퀴즈 졸업 축하해! (주니에게 선물을 요청하세요.)"
    elif ratio >= 0.7:
      user_title = "✨ 규은핑 얼마 안 남았어 이대로 멈춰!?"
    elif ratio >= 0.4:
      user_title = "📚 규은핑.. 열심히 말고 잘하자"
    else:
      user_title = "😭 규은핑.. 공부 말고 다른 재능을 찾아볼까?"

    st.session_state["last_score"] = score
    st.session_state["total_len"] = total_len
    st.session_state["user_title"] = user_title
    st.session_state["wrong_list"] = wrong_list

    st.info(
        f"**총점: {score} / {total_len}점**\n\n"
        f"👑 **나의 칭호**: {user_title}"
    )

  # [오답 노트 모드] 틀린 문제가 있을 때 표시
  if (
      "wrong_list" in st.session_state
      and len(st.session_state["wrong_list"]) > 0
  ):
    st.markdown("---")
    st.error(
        f"🚨 **오답 노트 알림**: 틀린 문제({len(st.session_state['wrong_list'])}개)가"
        " 있습니다!"
    )
    if st.button("❌ 틀린 문제만 모아서 다시 풀기"):
      st.session_state["questions"] = st.session_state["wrong_list"]
      del st.session_state["last_score"]
      del st.session_state["wrong_list"]
      st.rerun()

  # 채점 완료 후 결과 공유 버튼
  if "last_score" in st.session_state:
    score = st.session_state["last_score"]
    total = st.session_state["total_len"]
    title = st.session_state["user_title"]
    share_text = f"📚 [규은핑의 문제 생성기]\n✨ 시험 결과: 총점 {score} / {total}점\n👑 칭호: {title}\n준피티와 함께 공부 완료! 🎉"

    st.markdown("### 📤 결과 공유하기")

    share_html = f"""
        <div style="display: flex; gap: 10px; justify-content: center;">
            <button onclick="shareResult()" style="background-color: #fee500; color: #191919; border: none; padding: 12px 20px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                💬 카카오톡 / SNS로 점수 공유하기
            </button>
        </div>
        <script>
        function shareResult() {{
            const text = `{share_text}`;
            if (navigator.share) {{
                navigator.share({{
                    title: '규은핑의 문제 생성기 결과',
                    text: text,
                }}).catch(() => {{}});
            }} else {{
                navigator.clipboard.writeText(text).then(() => {{
                    alert('결과가 클립보드에 복사되었습니다! 카카오톡에 붙여넣기 하세요.');
                }});
            }}
        }}
        </script>
        """
    components.html(share_html, height=60)

  st.markdown("---")
  # 추가 20문제 생성 버튼
  if uploaded_files and api_key:
    if st.button("➕ 20문제 더 만들기"):
      if generate_questions(20):
        st.rerun()
