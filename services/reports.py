from sqlalchemy import func
from models import db, Issue, IssueLine, Item, Teacher, Department

def get_stats():
    # KPI Stats
    total_issues = Issue.query.count()
    total_items_issued = db.session.query(func.coalesce(func.sum(IssueLine.qty), 0)).scalar()
    
    return {
        'total_issues': total_issues,
        'total_items_issued': total_items_issued
    }

def get_top_items(limit=5):
    return db.session.query(
        Item.name, func.sum(IssueLine.qty).label('total_qty')
    ).join(IssueLine).group_by(Item.id).order_by(func.sum(IssueLine.qty).desc()).limit(limit).all()

def get_teacher_totals():
    return db.session.query(
        Teacher.name, func.count(Issue.id).label('issue_count'), func.sum(IssueLine.qty).label('item_count')
    ).join(Issue).join(IssueLine).group_by(Teacher.id).all()

def get_department_totals():
    return db.session.query(
        Department.name, func.sum(IssueLine.qty).label('item_count')
    ).select_from(Department).join(Teacher).join(Issue).join(IssueLine).group_by(Department.id).all()
