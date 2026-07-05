from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///edgetwin.db')
with engine.begin() as conn:
    conn.execute(text("UPDATE users SET user_id = replace(user_id, '-', '')"))
    conn.execute(text("UPDATE mechanics SET mechanic_id = replace(mechanic_id, '-', '')"))
    conn.execute(text("UPDATE mechanics SET current_assignment_id = replace(current_assignment_id, '-', '') WHERE current_assignment_id IS NOT NULL"))
    conn.execute(text("UPDATE machines SET machine_id = replace(machine_id, '-', '')"))
    conn.execute(text("UPDATE machines SET assigned_operator_id = replace(assigned_operator_id, '-', '') WHERE assigned_operator_id IS NOT NULL"))
print('Done!')
