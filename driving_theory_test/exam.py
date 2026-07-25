import uuid
from datetime import datetime

import math
import urllib.parse
from flask import Blueprint, redirect, render_template, request, url_for, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt, unset_jwt_cookies, set_access_cookies, create_access_token

from driving_theory_test.models import ExamQuestions
from driving_theory_test.utils import format_duration, update_user_token

bp = Blueprint("exam", __name__, url_prefix="/exam")

ExamQuestions.load_bank("./driving_theory_test/questions_bank.csv", "en")
ExamQuestions.load_bank("./driving_theory_test/questions_bank_mm.csv", "mm")


def _get_report_url(question_id) -> str:
    return "mailto:lostintime101dev@gmail.com?" + urllib.parse.urlencode({"subject": f"Issue question #{question_id}"})


@bp.route("/get_answer", methods=["POST"])
@jwt_required()
def get_answer():
    claims = get_jwt()
    if claims.get("training_mode"):
        answers: list = claims.get("answers")
        qid = answers[claims.get("current_index")][0]
        question_en = ExamQuestions.get_question_id(qid, "en")
        question_mm = ExamQuestions.get_question_id(qid, "mm")
        return jsonify({
            "ans_id": question_en["ans_num"],
            "en": {"ans_txt": question_en["ans_txt"], "ans_pic": question_en["ans_pic"]},
            "mm": {"ans_txt": question_mm["ans_txt"], "ans_pic": question_mm["ans_pic"]}
        })
    return make_response(jsonify({"error": "Exam mode... No cheating!"}), 400)


@bp.route("/results", methods=["GET"])
@jwt_required()
def results():
    claims = get_jwt()
    current_index = claims.get("current_index")
    answers: list = claims.get("answers")
    time_elapsed: float = claims.get("time_elapsed")
    time_remaining: float = claims.get("time_remaining")
    number_of_questions: int = int(claims.get("number_of_questions"))
    time_up = False
    if datetime.now().timestamp() > claims.get("end_exam"):
        time_up = True
    failed_questions = []
    score = 0
    #  Compute result
    for answer in answers:
        qid = answer[0]
        question_en = ExamQuestions.get_question_id(qid, "en")
        question_mm = ExamQuestions.get_question_id(qid, "mm")
        if question_en["ans_num"] == answer[1]:
            score += 1
        else:
            def _pick_ans(q, ans_num):
                if ans_num == "1":
                    return {"txt": q["a1_txt"], "pic": q["a1_pic"]}
                if ans_num == "2":
                    return {"txt": q["a2_txt"], "pic": q["a2_pic"]}
                if ans_num == "3":
                    return {"txt": q["a3_txt"], "pic": q["a3_pic"]}
                if ans_num == "4":
                    return {"txt": q["a4_txt"], "pic": q["a4_pic"]}
                return {"txt": None, "pic": None}
            user_en = _pick_ans(question_en, answer[1])
            user_mm = _pick_ans(question_mm, answer[1])
            wrong_answer = {
                "q_id": qid,
                "en": {
                    "quest_txt": question_en["q_txt"],
                    "quest_pic": question_en["q_pic"],
                    "true_txt": question_en["ans_txt"],
                    "true_pic": None,
                    "user_txt": user_en["txt"],
                    "user_pic": user_en["pic"],
                },
                "mm": {
                    "quest_txt": question_mm["q_txt"],
                    "quest_pic": question_mm["q_pic"],
                    "true_txt": question_mm["ans_txt"],
                    "true_pic": None,
                    "user_txt": user_mm["txt"],
                    "user_pic": user_mm["pic"],
                },
            }
            failed_questions.append(wrong_answer)

    percent_s = int((score / number_of_questions) * 100)
    pass_fail = "FAIL🥹"
    if percent_s >= 90:
        pass_fail = "PASS🥳"

    if not time_elapsed or not time_remaining:
        time_elapsed = datetime.now().timestamp() - float(claims.get("start_time"))
        time_remaining = float(claims.get("end_exam")) - datetime.now().timestamp()
        if time_remaining < 0:
            time_remaining = 0

    resp = make_response(
        render_template(
            "exam/results.html",
            total_quest=number_of_questions,
            total_correct=score,
            pass_fail=pass_fail,
            percent_score=percent_s,
            time_elapsed=format_duration(time_elapsed),
            time_remaining=format_duration(time_remaining),
            time_up=time_up,
            time_per_quest=math.ceil(time_elapsed / number_of_questions),
            failed_questions=failed_questions,
        )
    )
    update_user_token(
        resp,
        claims,
        answers=answers,
        current_index=current_index,
        time_elapsed=time_elapsed,
        score=score,
        time_remaining=time_remaining,
    )
    return resp


# standard question page template
@bp.route("/", methods=["GET", "POST"])
@jwt_required()
def exam():
    claims = get_jwt()
    if claims.get("score", False):
        return redirect(url_for("exam.results"))
    current_index = claims.get("current_index")
    answers: list = claims.get("answers")
    training_mode: bool = claims.get("training_mode")
    number_of_questions: int = int(claims.get("number_of_questions"))

    seconds_left = float(claims.get("end_exam")) - datetime.now().timestamp()

    # check for time up. If so, send user to results page
    if datetime.now().timestamp() > claims.get("end_exam"):
        return make_response(redirect(url_for("exam.results")))
    if current_index >= len(answers):
        # End exam
        return redirect(url_for("exam.results"))
    # update question bank with info from previous question
    if request.method == "POST":
        data = request.form
        # answer == 0 means the user clicked 'previous' or 'next' button, question bank should not be updated
        if data["Answer"] != "0":
            answers[current_index][1] = data["Answer"]
        current_index += 1
        resp = make_response(redirect(url_for("exam.exam")))
    else:
        qid = answers[current_index][0]
        question_en = ExamQuestions.get_question_id(qid, "en")
        question_mm = ExamQuestions.get_question_id(qid, "mm")
        question_formatted = {
            "id": qid,
            "en": {
                "question_text": question_en["q_txt"],
                "question_pic": question_en["q_pic"],
                "answers": {
                    "1": {"text": question_en["a1_txt"], "pic": question_en["a1_pic"]},
                    "2": {"text": question_en["a2_txt"], "pic": question_en["a2_pic"]},
                    "3": {"text": question_en["a3_txt"], "pic": question_en["a3_pic"]},
                    "4": {"text": question_en["a4_txt"], "pic": question_en["a4_pic"]}
                }
            },
            "mm": {
                "question_text": question_mm["q_txt"],
                "question_pic": question_mm["q_pic"],
                "answers": {
                    "1": {"text": question_mm["a1_txt"], "pic": question_mm["a1_pic"]},
                    "2": {"text": question_mm["a2_txt"], "pic": question_mm["a2_pic"]},
                    "3": {"text": question_mm["a3_txt"], "pic": question_mm["a3_pic"]},
                    "4": {"text": question_mm["a4_txt"], "pic": question_mm["a4_pic"]}
                }
            },
            "user_ans": answers[current_index][1] if len(answers[current_index]) else 0
        }

        resp = make_response(
            render_template(
                "exam/question.html",
                total=number_of_questions,
                question=question_formatted,
                current_index=current_index,
                seconds=seconds_left,
                training_mode=training_mode,
                progress=int((current_index / number_of_questions) * 100),
                report_url=_get_report_url(qid)
            )
        )

    update_user_token(resp, claims, answers=answers, current_index=current_index)
    # serves up new question data to template
    return resp


# user navigates backwards using "previous button", revised question page template
@bp.route("/p", methods=["POST"])
@jwt_required()
def previous_exam():
    claims = get_jwt()
    current_index = claims.get("current_index")
    if current_index > 0:
        current_index -= 1
    resp = make_response(redirect(url_for("exam.exam")))
    update_user_token(resp, claims, current_index=current_index)
    return resp


@bp.route("/start_exam", methods=["POST"])
@jwt_required()
def start_exam():
    claims = get_jwt()
    resp = make_response(redirect(url_for("exam.exam")))
    update_user_token(
        resp,
        claims,
        current_index=0,
        start_time=datetime.now().timestamp(),
        end_exam=datetime.now().timestamp() + int(claims.get("number_of_questions")) * 60,
    )
    return resp


@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    resp = make_response(redirect(url_for("home.home")))
    unset_jwt_cookies(resp)
    return resp


# Pre-exam page with instructions for user
@bp.route("/pre-exam", methods=["POST"])
def pre_exam():
    data = request.form
    if "exam_type" not in data.keys():
        return redirect(url_for('home.home'))
    exam_type = data.get("exam_type")
    number_of_questions = 50 if exam_type == "Full Exam" else 10
    resp = make_response(redirect(url_for("exam.pre_exam")))
    lang = data.get("lang", "en")
    exam_data = {
        "exam_type": exam_type,
        "training_mode": True if data.get("training_mode", False) else False,
        "number_of_questions": str(number_of_questions),
        "answers": [],
        "lang": lang,
    }
    for selected_question in ExamQuestions.create_question_bank(number_of_questions, lang):
        # Q_id, user answer
        exam_data["answers"].append(
            (
                selected_question,
                0,
            )
        )
    set_access_cookies(resp, create_access_token(uuid.uuid4().hex[:10].upper(), additional_claims=exam_data))
    return resp


@bp.route("/pre-exam", methods=["GET"])
@jwt_required()
def get_pre_exam():
    claims = get_jwt()
    if "number_of_questions" not in claims:
        return redirect(url_for('home.home'))
    return make_response(
        render_template("exam/pre-exam.html",
                        number_of_questions=claims.get("number_of_questions"))
    )
