from playhouse.shortcuts import model_to_dict, update_model_from_dict
from typing import List
from typing_extensions import TypedDict

import auth
from api.socket.constants import GAME_NS
from app import app, sio
from models import Group, PlayerRoom, Shape
from state.game import game_state
from utils import logger


class ServerGroup(TypedDict):
    uuid: str
    character_set: List[str]
    creation_order: str


class MemberBadge(TypedDict):
    uuid: str
    badge: int


class GroupJoin(TypedDict):
    group_id: str
    members: List[MemberBadge]


class LeaveGroup(TypedDict):
    uuid: str
    group_id: str


@sio.on("Group.Info.Get", namespace=GAME_NS)
@auth.login_required(app, sio)
async def get_group_info(sid: str, group_id: str):
    try:
        group = Group.get_by_id(group_id)
    except Group.DoesNotExist:
        logger.exception(f"Could not retrieve group information for {group_id}")
        data = {}
    else:
        data = model_to_dict(group)

    await sio.emit("Group.Info", data=data, room=sid, namespace=GAME_NS)


@sio.on("Group.Update", namespace=GAME_NS)
@auth.login_required(app, sio)
async def update_group(sid: str, group_info: ServerGroup):
    pr: PlayerRoom = game_state.get(sid)

    try:
        group = Group.get_by_id(group_info["uuid"])
    except Group.DoesNotExist:
        logger.exception(
            f"Could not retrieve group information for {group_info['uuid']}"
        )
    else:
        update_model_from_dict(group, group_info)
        group.save()

    for psid, _ in game_state.get_users(room=pr.room):
        await sio.emit(
            "Group.Update",
            group_info,
            room=psid,
            skip_sid=sid,
            namespace=GAME_NS,
        )


@sio.on("Group.Members.Update", namespace=GAME_NS)
@auth.login_required(app, sio)
async def update_group_badges(sid: str, member_badges: List[MemberBadge]):
    pr: PlayerRoom = game_state.get(sid)

    for member in member_badges:
        try:
            shape = Shape.get_by_id(member["uuid"])
        except Shape.DoesNotExist:
            logger.exception(
                f"Could not update shape badge for unknown shape {member['uuid']}"
            )
        else:
            shape.badge = member["badge"]
            shape.save()

    for psid, player in game_state.get_users(room=pr.room):
        await sio.emit(
            "Group.Members.Update",
            member_badges,
            room=psid,
            skip_sid=sid,
            namespace=GAME_NS,
        )


@sio.on("Group.Create", namespace=GAME_NS)
@auth.login_required(app, sio)
async def create_group(sid: str, group_info: ServerGroup):
    pr: PlayerRoom = game_state.get(sid)

    try:
        Group.get_by_id(group_info["uuid"])
        logger.exception(f"Group with {group_info['uuid']} already exists")
        return
    except Group.DoesNotExist:
        Group.create(**group_info)

    for psid, _ in game_state.get_users(room=pr.room):
        await sio.emit(
            "Group.Create",
            group_info,
            room=psid,
            skip_sid=sid,
            namespace=GAME_NS,
        )


@sio.on("Group.Join", namespace=GAME_NS)
@auth.login_required(app, sio)
async def join_group(sid: str, group_join: GroupJoin):
    pr: PlayerRoom = game_state.get(sid)

    group_ids = set()

    for member in group_join["members"]:
        try:
            shape = Shape.get_by_id(member["uuid"])
        except Shape.DoesNotExist:
            logger.exception(
                f"Could not update shape group for unknown shape {member['uuid']}"
            )
        else:
            if shape.group is not None and shape.group != group_join["group_id"]:
                group_ids.add(shape.group)
            shape.group = group_join["group_id"]
            shape.badge = member["badge"]
            shape.save()

    # Group joining can be the result of a merge or a split and thus other groups might be empty now
    for group_id in group_ids:
        await remove_group_if_empty(group_id)

    for psid, _ in game_state.get_users(room=pr.room):
        await sio.emit(
            "Group.Join",
            group_join,
            room=psid,
            skip_sid=sid,
            namespace=GAME_NS,
        )


@sio.on("Group.Leave", namespace=GAME_NS)
@auth.login_required(app, sio)
async def leave_group(sid: str, client_shapes: List[LeaveGroup]):
    pr: PlayerRoom = game_state.get(sid)

    group_ids = set()

    for client_shape in client_shapes:
        try:
            shape = Shape.get_by_id(client_shape["uuid"])
        except Shape.DoesNotExist:
            logger.exception(
                f"Could not remove shape group for unknown shape {client_shape['uuid']}"
            )
        else:
            group_ids.add(client_shape["group_id"])
            shape.group = None
            shape.show_badge = False
            shape.save()

    for group_id in group_ids:
        await remove_group_if_empty(group_id)

    for psid, _ in game_state.get_users(room=pr.room):
        await sio.emit(
            "Group.Leave",
            client_shapes,
            room=psid,
            skip_sid=sid,
            namespace=GAME_NS,
        )


@sio.on("Group.Remove", namespace=GAME_NS)
@auth.login_required(app, sio)
async def remove_group(sid: str, group_id: str):
    pr: PlayerRoom = game_state.get(sid)

    for shape in Shape.filter(group_id=group_id).select():
        shape.group = None
        shape.show_badge = False
        shape.save()

    # check if group still has members
    await remove_group_if_empty(group_id)

    for psid, _ in game_state.get_users(room=pr.room):
        await sio.emit(
            "Group.Remove",
            group_id,
            room=psid,
            skip_sid=sid,
            namespace=GAME_NS,
        )


async def remove_group_if_empty(group_id: str):
    try:
        group = Group.get_by_id(group_id)
    except Group.DoesNotExist:
        return

    if Shape.filter(group=group_id).count() == 0:
        group.delete_instance(True)
