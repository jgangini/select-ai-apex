from __future__ import annotations

NAVIGATION_CSS = b"""
#t_Header .t-Header-controls #t_Button_navControl {
  display: grid;
  place-items: center;
  inline-size: 44px;
  block-size: 44px;
  padding: 0;
}

#t_Header #t_Button_navControl > .t-Header-controlsIcon {
  inset: 0;
  margin: auto;
}
"""

RAIL_NAVIGATION_CSS = b"""
#t_Header .t-Header-controls:has(> #t_Button_navControl) {
  margin-inline: -4px 4px;
}

#t_TreeNav .a-TreeView-content > :is(.fa, .fa-solid) {
  position: relative;
  inset-inline-start: 8px;
  text-align: center;
}
"""


def apply_ask_oracle_navigation(connection, workspace: str, application_id: int) -> bool:
    import oracledb

    with connection.cursor() as cursor:
        cursor.callproc("apex_util.set_workspace", [workspace])
        cursor.execute(
            """select application_file_id, mime_type, file_charset, file_content
               from apex_application_static_files
               where application_id = :application_id and workspace = :workspace
                 and file_name = 'custom_app_file.css'""",
            application_id=application_id,
            workspace=workspace,
        )
        asset = cursor.fetchone()
        if asset is None:
            return False
        file_id, mime_type, charset, content_lob = asset
        content = content_lob.read()
        missing_styles = b"".join(
            style for style in (NAVIGATION_CSS, RAIL_NAVIGATION_CSS) if style not in content
        )
        if not missing_styles:
            return False

        cursor.setinputsizes(content=oracledb.DB_TYPE_BLOB)
        cursor.execute(
            """begin
                 wwv_flow_imp_shared.remove_app_static_file(
                   p_id => :file_id, p_flow_id => :application_id);
                 wwv_flow_imp_shared.create_app_static_file(
                   p_id => :file_id, p_flow_id => :application_id,
                   p_file_name => 'custom_app_file.css', p_mime_type => :mime_type,
                   p_file_charset => :charset, p_file_content => :content);
               end;""",
            file_id=file_id,
            application_id=application_id,
            mime_type=mime_type,
            charset=charset,
            content=content + missing_styles,
        )
    connection.commit()
    return True
