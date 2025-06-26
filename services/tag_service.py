from models import db, Tag

def get_all_tags_for_user(user_id):
    return Tag.query.filter_by(user_id=user_id).all()

def create_tag(user_id, name, color):
    if not name:
        return None, 'Tag name is required.'

    existing_tag = Tag.query.filter_by(user_id=user_id, name=name).first()
    if existing_tag:
        return None, f'A tag named "{name}" already exists.'

    tag = Tag(name=name, color=color, user_id=user_id)
    db.session.add(tag)
    db.session.commit()
    return tag, f'Tag "{name}" created successfully.'

def edit_tag(user_id, tag_id, name, color):
    tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
    if not tag:
        return None, 'Tag not found.'

    if not name:
        return None, 'Tag name is required.'

    existing_tag = Tag.query.filter_by(user_id=user_id, name=name).first()
    if existing_tag and existing_tag.id != tag.id:
        return None, f'A tag named "{name}" already exists.'

    tag.name = name
    tag.color = color
    db.session.commit()
    return tag, f'Tag "{name}" updated successfully.'

def delete_tag(user_id, tag_id):
    tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
    if not tag:
        return False, 'Tag not found.'

    for entry in tag.entries:
        entry.tags.remove(tag)

    db.session.delete(tag)
    db.session.commit()
    return True, f'Tag "{tag.name}" deleted successfully.'
