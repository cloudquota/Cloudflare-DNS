import streamlit as st
import requests
from typing import Dict, Any, Optional, Tuple, List

st.set_page_config(page_title="Cloudflare DNS 面板", layout="wide")

CF_API_BASE = "https://api.cloudflare.com/client/v4"
DNS_TYPES = ["A", "AAAA", "CNAME", "TXT", "MX", "NS", "SRV", "CAA"]
TTL_OPTIONS = [1, 60, 120, 300, 600, 1800, 3600, 7200, 86400]


def cf_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token.strip()}", "Content-Type": "application/json"}


def extract_error(data: Any) -> str:
    if isinstance(data, dict) and data.get("errors"):
        return "；".join(f"[{e.get('code')}] {e.get('message')}" for e in data["errors"])
    return str(data.get("message", "未知错误")) if isinstance(data, dict) else "未知错误"


def cf_request(
    method: str,
    path: str,
    token: str,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Dict[str, Any], str]:
    try:
        r = requests.request(
            method,
            CF_API_BASE + path,
            headers=cf_headers(token),
            params=params,
            json=json,
            timeout=20,
        )
        data = r.json()
    except Exception as e:
        return False, {}, f"请求失败：{e}"

    if not r.ok or data.get("success") is False:
        return False, data, extract_error(data)

    return True, data, ""


def ttl_label(v: int) -> str:
    return "自动" if v == 1 else f"{v} 秒"


@st.cache_data(ttl=60)
def get_zones_cached(token: str) -> List[Dict[str, Any]]:
    zones = []
    page = 1
    while True:
        ok, data, err = cf_request("GET", "/zones", token, params={"page": page, "per_page": 50})
        if not ok:
            raise RuntimeError(err)
        zones.extend(data.get("result", []))
        if page >= data.get("result_info", {}).get("total_pages", 1):
            break
        page += 1
    return zones


def list_dns(token: str, zone_id: str) -> List[Dict[str, Any]]:
    ok, data, err = cf_request(
        "GET",
        f"/zones/{zone_id}/dns_records",
        token,
        params={"page": 1, "per_page": 100},
    )
    if not ok:
        raise RuntimeError(err)
    return data.get("result", [])


def update_dns(token: str, zone_id: str, record_id: str, payload: Dict[str, Any]):
    ok, _, err = cf_request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", token, json=payload)
    if not ok:
        raise RuntimeError(err)


def delete_dns(token: str, zone_id: str, record_id: str):
    ok, _, err = cf_request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}", token)
    if not ok:
        raise RuntimeError(err)


def create_dns(token: str, zone_id: str, payload: Dict[str, Any]):
    ok, _, err = cf_request("POST", f"/zones/{zone_id}/dns_records", token, json=payload)
    if not ok:
        raise RuntimeError(err)


# ---------------- UI ----------------

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; }
      [data-testid="stSidebar"] { min-width: 320px; max-width: 320px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("☁️ Cloudflare DNS 面板")


with st.sidebar:
    st.header("🔐 认证（不保存）")
    token_input = st.text_input("Cloudflare API Token", type="password", placeholder="粘贴 Token…")

    cA, cB = st.columns(2)
    with cA:
        if st.button("使用 Token", use_container_width=True):
            if token_input.strip():
                st.session_state["cf_token"] = token_input.strip()
                # 清掉缓存，避免 token 换了 zones 还用旧缓存
                get_zones_cached.clear()
    with cB:
        if st.button("清除 Token", use_container_width=True):
            st.session_state.pop("cf_token", None)
            st.session_state.pop("zones", None)
            get_zones_cached.clear()
            st.success("已清除（不会保存）")

token = st.session_state.get("cf_token")
if not token:
    st.info("请在左侧输入 Token → 点击「使用 Token」")
    st.stop()



# zones
try:
    zones = get_zones_cached(token)
except Exception as e:
    st.error(f"获取 Zones 失败：{e}")
    st.stop()

if not zones:
    st.warning("没有获取到 Zone。请检查 Token 权限（Zone:Read + DNS:Edit）")
    st.stop()

zone_map = {z["name"]: z["id"] for z in zones}
zone_name = st.selectbox("选择域名（Zone）", sorted(zone_map.keys()))
zone_id = zone_map[zone_name]

colL, colR = st.columns([3, 2])

with colR:
    with st.container(border=True):
        st.subheader("➕ 新增 DNS")
        with st.form("create_form", clear_on_submit=True):
            rtype = st.selectbox("类型", DNS_TYPES)
            name = st.text_input("Name", placeholder="例如：test.example.com 或 @")
            content = st.text_input("Content", placeholder="例如：1.2.3.4 / target.domain.com / 文本…")
            ttl = st.selectbox("TTL", TTL_OPTIONS, format_func=ttl_label, index=0)
            proxied = st.checkbox("开启 Cloudflare 代理（proxied）", value=False)

            submitted = st.form_submit_button("创建记录", use_container_width=True)
            if submitted:
                try:
                    create_dns(
                        token,
                        zone_id,
                        {
                            "type": rtype,
                            "name": name.strip(),
                            "content": content.strip(),
                            "ttl": ttl,
                            "proxied": proxied,
                        },
                    )
                    st.success("创建成功")
                    st.rerun()
                except Exception as e:
                    st.error(f"创建失败：{e}")

with colL:
    st.subheader(f"📄 DNS 记录管理 - {zone_name}")

    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
    with ctrl1:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    with ctrl2:
        only_proxied = st.toggle("仅显示代理", value=False)
    with ctrl3:
        keyword = st.text_input("搜索（name/content）", placeholder="输入关键字…")

    try:
        records = list_dns(token, zone_id)
    except Exception as e:
        st.error(f"拉取 DNS 记录失败：{e}")
        st.stop()

    # 过滤
    if only_proxied:
        records = [r for r in records if r.get("proxied")]
    if keyword.strip():
        k = keyword.strip().lower()
        records = [
            r
            for r in records
            if k in str(r.get("name", "")).lower() or k in str(r.get("content", "")).lower()
        ]

    st.caption(f"共 {len(records)} 条记录（显示结果）")

    if not records:
        st.info("暂无记录或被筛选条件过滤")
        st.stop()

    # 用 expander 分组展示（比全表格更适合 CRUD）
    for r in records:
        rid = r["id"]
        status = "🟠 代理" if r.get("proxied") else "⚪ 仅 DNS"
        title = f"{status} | {r['type']}  {r['name']}  →  {r.get('content','')}"
        with st.expander(title, expanded=False):
            c1, c2, c3, c4 = st.columns([2.2, 2.5, 1.2, 1.3])
            with c1:
                name = st.text_input("Name", r["name"], key=f"name_{rid}")
            with c2:
                content = st.text_input("Content", r.get("content", ""), key=f"content_{rid}")
            with c3:
                ttl = st.selectbox(
                    "TTL",
                    TTL_OPTIONS,
                    format_func=ttl_label,
                    index=TTL_OPTIONS.index(r["ttl"]) if r.get("ttl") in TTL_OPTIONS else 0,
                    key=f"ttl_{rid}",
                )
            with c4:
                proxied = st.checkbox("Proxied", r.get("proxied", False), key=f"px_{rid}")

            b1, b2, b3 = st.columns([1, 1, 1])
            with b1:
                if st.button("💾 保存", key=f"save_{rid}", use_container_width=True):
                    try:
                        update_dns(
                            token,
                            zone_id,
                            rid,
                            {
                                "type": r["type"],
                                "name": name.strip(),
                                "content": content.strip(),
                                "ttl": ttl,
                                "proxied": proxied,
                            },
                        )
                        st.success("已保存")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存失败：{e}")

            with b2:
                confirm = st.checkbox("确认删除", key=f"confirm_{rid}")
                if st.button("🗑 删除", key=f"del_{rid}", disabled=not confirm, use_container_width=True):
                    try:
                        delete_dns(token, zone_id, rid)
                        st.success("已删除")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败：{e}")

            with b3:
                st.write("")  # 占位对齐
