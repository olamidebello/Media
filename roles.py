ADMIN_ROLES=('admin','superadmin')
ROLES=('viewer','creator','admin','superadmin')
def actor_role(c,actor):
    row=c.execute('SELECT role FROM users WHERE id=?',(actor,)).fetchone()
    if not row:raise PermissionError('Account unavailable')
    return row[0]
def protect(c,actor,targets):
    if actor_role(c,actor)=='superadmin':return
    for target in targets:
        row=c.execute('SELECT role FROM users WHERE id=?',(int(target),)).fetchone()
        if row and row[0]=='superadmin':raise PermissionError('Only a super admin can manage a super admin account')
def validate_role(c,actor,role):
    if role not in ROLES:raise ValueError('Invalid role')
    if role=='superadmin' and actor_role(c,actor)!='superadmin':raise PermissionError('Only a super admin can grant super admin access')
