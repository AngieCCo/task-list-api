from sqlalchemy import asc, desc
from app import db
from app.models.task import Task
from datetime import datetime
from flask import Blueprint, jsonify, make_response, request, abort
import os
from slack_sdk import WebClient

def get_valid_item_by_id(model, id):
    try:
        id = int(id)
    except:
        abort(make_response({'details': "Invalid data"}, 400))

    item = model.query.get(id)
    return item if item else abort(make_response({'message': f"Task {id} not found"}, 404))


task_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

@task_bp.route("", methods=["POST"])
def create_task():
    
    # To be able to read the request we need to use the .getj_son() method
    request_body = request.get_json()

    if not "title" in request_body or not "description" in request_body:
        return make_response({"details": "Invalid data"}, 400)

    new_task = Task.dict_for_post_method(request_body)
    db.session.add(new_task)
    db.session.commit()

    return {"task": new_task.to_dict()}, 201


@task_bp.route("", methods=["GET"])
def get_all_tasks():

    # get 1 task by param
    query_request = request.args.get("sort")
    if query_request == "asc":
        tasks = Task.query.order_by(Task.title.asc())
    elif query_request == "desc":
        tasks = Task.query.order_by(Task.title.desc())
    # get all tasks
    else:
        tasks = Task.query.all()

    tasks_response = []

    for task in tasks:
        tasks_response.append(task.to_dict())
    return jsonify(tasks_response), 200


@task_bp.route("/<task_id>", methods=["GET"])
def handle_task(task_id):

    task: Task = get_valid_item_by_id(Task, task_id)

    if not task.goal_id:
        return {"task": task.to_dict()}, 200
    else:
        return {"task": task.to_dict_with_goal_id()}, 200


@task_bp.route("/<task_id>", methods=["PUT"])
def update_one_task(task_id):

    request_body = request.get_json()
    task_is_valid: Task = get_valid_item_by_id(Task, task_id)

    task_is_valid.title = request_body["title"]
    task_is_valid.description = request_body["description"]

    db.session.commit()

    return {"task": task_is_valid.to_dict()}, 200


@task_bp.route("/<task_id>", methods=["DELETE"])
def delete_one_task(task_id):
    
    task_to_delete: Task = get_valid_item_by_id(Task, task_id)

    db.session.delete(task_to_delete)
    db.session.commit()

    title_task = task_to_delete.title

    return {"details": f'Task {task_id} "{title_task}" successfully deleted'}, 200



@task_bp.route("/<task_id>/mark_complete", methods=["PATCH"])
def mark_task_as_completed(task_id):

    task_is_valid: Task = get_valid_item_by_id(Task, task_id)
    task_is_valid.completed_at = datetime.utcnow()

    db.session.commit()
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    response = client.chat_postMessage(channel="task-list-api",
                                    text="Task completed")

    return {"task": task_is_valid.to_dict()}, 200


@task_bp.route("/<task_id>/mark_incomplete", methods=["PATCH"])
def mark_task_as_incompleted(task_id):

    task_is_valid: Task = get_valid_item_by_id(Task, task_id)

    task_is_valid.completed_at = None

    db.session.commit()

    return {"task": task_is_valid.to_dict()}, 200
