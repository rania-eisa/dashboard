import pandas as pd
import folium
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from streamlit_folium import st_folium

# -----------------------------------------
# 1. تحميل البيانات
# -----------------------------------------
@st.cache_data
def load_data():
    use_cols = ["LCLid", "day", "district", "latitude", "longitude", "status", "building"] + [f"hh_{i}" for i in range(48)]
    df = pd.read_csv("modified_data2.csv", usecols=use_cols, low_memory=False)
    df.rename(columns={"latitude": "lat", "longitude": "lon"}, inplace=True)
    df["day"] = pd.to_datetime(df["day"])

    df_sorted = df.sort_values(by=["LCLid", "day"], ascending=[True, False])
    df_unique = df_sorted.drop_duplicates(subset="LCLid", keep="first")

    statuses = ["normal", "fault", "leak"]
    df_sampled = pd.concat([
        df_unique[df_unique["status"] == s] for s in statuses if not df_unique[df_unique["status"] == s].empty
    ])
    return df_sampled

df = load_data()
time_cols = [col for col in df.columns if col.startswith("hh_")]

# -----------------------------------------
# 2. إعداد الصفحة من اليمين لليسار + تصميم داكن
# -----------------------------------------
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    body { direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; background-color: #2f2f2f}
    .css-18ni7ap { flex-direction: row-reverse; }
    .stApp {
        background-color: #2f2f2f;
        color: white;
    }
    h1, h2, h3, h4, h5, h6, label {
        color: white;
    }
    .card {
        background-color: #3e3e3e;
        padding: 20px;
        margin-bottom: 20px;
        border-radius: 15px;
        border: 1px solid #555;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

st.title("لوحة متابعة العدادات الذكية")

# -----------------------------------------
# 3. فلاتر التصفية
# -----------------------------------------
with st.sidebar:
    st.header("خيارات التصفية")
    start_date = st.date_input("تاريخ البداية", df["day"].min().date())
    end_date = st.date_input("تاريخ النهاية", df["day"].max().date())

    districts = df["district"].dropna().unique()
    selected_district = st.selectbox("اختر الحي", options=["الكل"] + sorted(districts))

    buildings = df["building"].dropna().unique()
    selected_type = st.selectbox("اختر نوع المبنى", options=["الكل"] + sorted(buildings))

# -----------------------------------------
# 4. تطبيق الفلاتر
# -----------------------------------------
mask = (df["day"] >= pd.to_datetime(start_date)) & (df["day"] <= pd.to_datetime(end_date))
if selected_district != "الكل":
    mask &= (df["district"] == selected_district)
if selected_type != "الكل":
    mask &= (df["building"] == selected_type)

filtered_df = df.loc[mask]

# -----------------------------------------
# 5. تحويل الحالة إلى العربية
# -----------------------------------------
status_map = {"normal": "سليم", "fault": "عطل في العداد", "leak": "تسريب"}
filtered_df["الحالة"] = filtered_df["status"].map(status_map).fillna("غير معروف")

# -----------------------------------------
# 6. التحليلات والرسوم البيانية
# -----------------------------------------
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### تحليلات العدادات")
    st.markdown(f"عدد العدادات: `{filtered_df['LCLid'].nunique()}`")

    st.subheader("توزيع الحالات")
    status_counts = filtered_df["الحالة"].value_counts().reset_index()
    status_counts.columns = ["الحالة", "عدد"]
    fig1 = px.bar(status_counts, x="الحالة", y="عدد", color="الحالة",
                  category_orders={"الحالة": ["سليم", "تسريب", "عطل في العداد", "غير معروف"]})
    st.plotly_chart(fig1, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("نسبة العدادات السليمة")
        total = len(filtered_df)
        normal = len(filtered_df[filtered_df["status"] == "normal"])
        percentage = round((normal / total) * 100, 1) if total > 0 else 0
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentage,
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "green"}},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={"text": "سليم (%)"}
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_b:
        st.subheader("نسبة كل حالة")
        fig3 = px.pie(filtered_df, names="الحالة", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("قائمة العدادات في الحي")
    st.dataframe(
        filtered_df[["LCLid", "district", "building", "الحالة"]].sort_values("district").reset_index(drop=True),
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # احسب متوسط الاستهلاك مباشرة بعد تصفية البيانات
filtered_df["متوسط_الاستهلاك"] = filtered_df[time_cols].mean(axis=1)

# متوسط استهلاك العدادات لكل حي
st.subheader("متوسط استهلاك العدادات لكل حي")
avg_by_district = filtered_df.groupby("district")["متوسط_الاستهلاك"].mean().reset_index()
fig_avg = px.bar(avg_by_district, x="district", y="متوسط_الاستهلاك",
                 labels={"district": "الحي", "متوسط_الاستهلاك": "متوسط الاستهلاك"},
                 color="district", text_auto=True)
st.plotly_chart(fig_avg, use_container_width=True)



# تغير متوسط الاستهلاك اليومي خلال الفترة
st.subheader("تغير متوسط الاستهلاك اليومي خلال الفترة")
daily_avg = filtered_df.groupby("day")["متوسط_الاستهلاك"].mean().reset_index()
fig_trend = px.line(daily_avg, x="day", y="متوسط_الاستهلاك",
                    labels={"day": "اليوم", "متوسط_الاستهلاك": "متوسط الاستهلاك"},
                    markers=True)
st.plotly_chart(fig_trend, use_container_width=True)

# توزيع العدادات حسب الحالة (بالإنجليزية)
st.subheader("توزيع العدادات حسب الحالة")
status_counts_eng = filtered_df["status"].value_counts().reset_index()
status_counts_eng.columns = ["status", "count"]
fig_pie = px.pie(status_counts_eng, values="count", names="status", title="حالة العدادات")
st.plotly_chart(fig_pie, use_container_width=True)



st.subheader("متوسط الاستهلاك حسب حالة العداد")
status_avg = filtered_df.groupby("status")["متوسط_الاستهلاك"].mean().reset_index()
status_avg["الحالة"] = status_avg["status"].map(status_map).fillna("غير معروف")
fig_status_avg = px.bar(status_avg, x="الحالة", y="متوسط_الاستهلاك",
                        color="الحالة", text_auto=True)
st.plotly_chart(fig_status_avg, use_container_width=True)


st.subheader("توزيع الاستهلاك حسب الأحياء")
fig_box = px.box(filtered_df, x="district", y="متوسط_الاستهلاك", color="district")
st.plotly_chart(fig_box, use_container_width=True)









# -----------------------------------------
# 7. الخريطة
# -----------------------------------------
with right_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### خريطة توزيع العدادات")
    if not filtered_df.empty:
        m = folium.Map(location=[filtered_df["lat"].mean(), filtered_df["lon"].mean()], zoom_start=13)
        color_map = {"سليم": "blue", "تسريب": "orange", "عطل في العداد": "red", "غير معروف": "gray"}
        for row in filtered_df.itertuples():
            folium.CircleMarker(
                location=[row.lat, row.lon],
                radius=5,
                color=color_map.get(row.الحالة, "gray"),
                fill=True,
                fill_opacity=0.7,
                popup=f"عداد: {row.LCLid}<br>الحالة: {row.الحالة}<br>نوع المبنى: {row.building}"
            ).add_to(m)
        st_folium(m, height=720, width=1400)
    else:
        st.warning("لا توجد بيانات متاحة لعرضها على الخريطة.")
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------
# 8. استهلاك عداد معين
# -----------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### تفاصيل استهلاك عداد محدد")

# تأكد من وجود البيانات المفلترة
if not filtered_df.empty:
    meter_ids = sorted(filtered_df["LCLid"].dropna().unique())

    # تحقق أن هناك عدادات متاحة للاختيار
    if len(meter_ids) > 0:
        selected_meter = st.selectbox("اختر العداد", options=meter_ids)

        # تصفية البيانات بناءً على العداد المحدد
        meter_data = filtered_df[filtered_df["LCLid"] == selected_meter]

        # تأكد من وجود بيانات لهذا العداد
        if not meter_data.empty:
            # حساب متوسط استهلاك كل نصف ساعة
            avg_consumption = meter_data[time_cols].mean()

            fig_meter = px.line(
                x=list(range(48)),
                y=avg_consumption.values,
                labels={"x": "نصف الساعة", "y": "الاستهلاك المتوسط"},
                title=f"متوسط استهلاك العداد {selected_meter}"
            )

            st.plotly_chart(fig_meter, use_container_width=True)
        else:
            st.info("لا توجد بيانات لهذا العداد في النطاق المحدد.")
    else:
        st.warning("لا توجد عدادات متاحة في البيانات المفلترة.")
else:
    st.warning("البيانات غير متوفرة أو النطاق المحدد لا يحتوي على نتائج.")
st.markdown('</div>', unsafe_allow_html=True)
