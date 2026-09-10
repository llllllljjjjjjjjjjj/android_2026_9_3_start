# 核心四类逐行分析：c23 / mp8 / qf7 / a15

> 签名/加密/上传链路的四个核心混淆类（`com.zj.widget` 包），源码来自脱壳 dump dex 反编译
> （`s_36_7445068.dex` / `s_41_5167656.dex`）。本文档逐字段、逐方法展开语义，并与动态实测交叉印证。

## 零、四类在链路中的角色总览

```
发起请求
  │
  ├─ 字段加密：EncryptInterceptor 用 c23.b() 取 encKey，对敏感字段 AES 加密
  │
  ├─ 请求签名：ParamsInterceptor.getSign 用 c23.d() 取 signKey
  │              = cq.c( h58.c(JSON), signKey )   ← AES(SHA256(json)旋转)
  │
  ├─ 上传轨迹：qf7.j 组装 pois body，内部用 c23.d() 算 sign
  │
  ├─ 上传步幅：qf7.l 组装 strideList body（外包数组）
  │
  ├─ 结束跑步：qf7.c → mp8.f 追加 runImgRecord + timestamp
  │              runImgRecord = a15.c( runRecordCode + "260826158.6.8"
  │                               + k14.a.c(hcj_bg_run_index) + timestamp )   ← a15.c = MD5
  │
  └─ MD5：a15.c = 标准 MD5 hex（小写）
```

---

## 一、c23.java —— 密钥/配置存储（getter 与字段错位混淆）

### 1. 字段（静态成员）语义

| 字段 | 类型 | 初始值 | 语义 | 实际值（动态确认） |
|------|------|--------|------|-------------------|
| `a` | String | `""` | **encKey**（字段加密 key） | `F44B0282BEA83557` |
| `b` | String | `""` | **signKey**（签名 key） | `F44B0282BEA83557` |
| `c` | String | `null` | str3（未用） | `""` |
| `f11070a` | List\<String\> | `null` | **敏感字段列表**（需 AES 加密的字段名） | `[phone,password,userName,schoolName,studentNumber]` |
| `f11071a` | volatile boolean | `false` | **初始化标志**（防止重复初始化） | 首次 e() 后 true |
| `f11072b` | boolean | `false` | z 参数（未用） | false |
| `f11073c` | boolean | `false` | z2 参数（未用） | false |

### 2. getter 与字段的错位映射（★最容易看错的地方）

方法名与返回字段**故意错位**，这是逆向最大的坑：

| getter 方法 | 返回的字段 | 实际含义 | 谁在用 |
|------------|-----------|---------|--------|
| `a()` | `c` | str3（空） | 几乎无用 |
| **`b()`** | **`a`** | **encKey** | EncryptInterceptor（字段加解密） |
| `c()` | `f11070a` | 敏感字段列表 | EncryptInterceptor（判断哪些字段加密） |
| **`d()`** | **`b`** | **signKey** | ParamsInterceptor.getSign / qf7.j（请求签名） |
| `f()` | `f11073c` | z2 | 未用 |
| `g()` | `f11072b` | z | 未用 |

> 🔴 关键结论：**字段加密用 `c23.b()`（返回字段 a），签名用 `c23.d()`（返回字段 b）**。
> 二者值碰巧相同（都是 `F44B0282BEA83557`），但 getter 不同——此前文档一度写成"sign key = c23.b"是错的。

### 3. 方法逐行语义

**构造器 `c23()`**：`throw new AssertionError("no instance!")` —— 纯静态工具类，不可实例化。

**`e(str, str2, str3, z, z2, list)`** —— 唯一写入口：
```java
if (f11071a) return;                    // 只初始化一次（volatile 标志）
if (!TextUtils.isEmpty(str)) {
    a = str; f11071a = true;            // 字段 a = encKey；置初始化标志
}
b = str2;                               // 字段 b = signKey
f11072b = z;  f11073c = z2;             // 两个布尔标志
c = str3;                               // 字段 c
f11070a = list;                         // 敏感字段列表
```

**调用点**（`k14.d` 网络库初始化，第 128 行）：
```java
c23.e(
    (g33.b()==9 || g33.b()==11) ? r01.e : r01.f,   // str  = "F44B0282BEA83557"(Pro/Sd) 或 "huachenjie"(其他)
    c(ctx, pwdResId),                              // str2 = k14.a.c(bg_contact_list) = K.b2s(图片像素)
    "",                                            // str3
    false, false,                                  // z, z2
    ["phone","password","userName","schoolName","studentNumber"]  // list
);
```

→ 故：`字段 a = r01.e = F44B0282BEA83557`；`字段 b = k14.a.c(bg_contact_list)`。
→ 而 `bg_contact_list` 是 **XML shape**（484 字节，`<shape>/<corners>/<solid>`），
   `BitmapFactory.decodeResource` 返回 null → `k14.a.c` fallback 返回 `r01.e`。
→ **所以 signKey = 字段 b = 也等于 `F44B0282BEA83557`**（fallback 机制，非"同一个 key"）。

---

## 二、mp8.java —— 阳光跑 API 封装（runImgRecord 生成点）

### 1. 字段

| 字段 | 类型 | 语义 |
|------|------|------|
| `a` | static ISunshineApi | Retrofit 接口单例（懒加载） |

### 2. 关键方法 `f(Map params)` —— ★runImgRecord 生成

```java
public static void f(Map<String, Object> params) {
    String str = (String) params.get("runRecordCode");
    if (str != null) {                                   // 仅结束类接口（含 runRecordCode）
        String strValueOf = String.valueOf(System.currentTimeMillis() + z70.B());
        params.put("runImgRecord", a15.c(                // MD5
            str + "260826158.6.8"                        //   runRecordCode + 版本号
            + k14.a.c(Utils.a(), R.drawable.hcj_bg_run_index)  // + 图片派生值(K.b2s)
            + strValueOf));                              //   + timestamp
        params.put("timestamp", strValueOf);
    }
}
```

语义：
- `timestamp = System.currentTimeMillis() + z70.B()`（`z70.B()` 是服务端时间偏移）。
- `runImgRecord = MD5( runRecordCode + "260826158.6.8" + 图片派生值 + timestamp )`。
- 图片派生值 = `k14.a.c(hcj_bg_run_index)` = `K.b2s(hcj_bg_run_index.png 像素, mode=1)` —— **native，待真实跑步触发采集**。

### 3. 结束跑步接口（都先调 `f()` 追加 runImgRecord）

| 方法 | 追加 runImgRecord | 对应 ISunshineApi | 接口 |
|------|------------------|-------------------|------|
| `a(Map)` | ✅ f(params) | `j().G` | finish（变体1） |
| `b(Map)` | ✅ f(params) | `j().c` | finish（变体2） |
| `i(Map)` | ✅ f(params) | `j().b` | finish（变体3） |

### 4. 其余 API 封装方法（接口映射）

| 方法 | 入参 | 对应 ISunshineApi | 业务 |
|------|------|-------------------|------|
| `D(param)` | StartRunPageParam | `j().e` | **开始跑 startSunRun** |
| `d(...)` | school/sub/target/activity/plan/fence/sportType | `j().m` | **检查配置 checkSunRunConfig** |
| `e(sportType)` | int | `j().a` | 未完成跑步 queryUnFinishRun |
| `h(fenceMap)` | Map | `j().E` | 查询围栏 |
| `v(schoolCode)` | String | `j().I` | 围栏列表 |
| `A(pageNum,sem,plan)` | — | `j().z` | 分页阳光跑记录 |
| `x(sem,plan,sportType)` | — | `j().k` | 阳光跑详情 |
| `u(semesterCode)` | String | `j().j` | 跑步计划列表 |
| `E(runRecordCode,declaration)` | — | `j().H` | 申诉 |
| `c(runRecordCode,problem,sem)` | — | `j().s` | 问题反馈 |
| `o(activityCode)` | — | `j().y` | 活动详情 |
| `p(sex,plan)` / `y` / `z` | — | `j().r/q/A` | 排名 |
| `n()` | — | `j().B` | 附近跑步标准 |
| `t()` | — | `j().F` | 结束横幅 |
| `k()` | — | `j().J` | 视频 |

> mp8 = 阳光跑（SunshineRun）的**所有**接口封装，qf7 = 跑步数据上传（Run）接口封装，两者分工不同。

---

## 三、qf7.java —— 跑步数据上传封装（sign 生成点）

### 1. 字段

| 字段 | 类型 | 语义 |
|------|------|------|
| `a` | static IRunApi | Retrofit 接口单例 |

### 2. 上传方法逐行语义（body 格式权威来源）

| 方法 | body 结构 | 对应 IRunApi | 接口 |
|------|----------|-------------|------|
| `h(paceList,paceInterval,runRecordCode)` | `{paceList,paceInterval,runRecordCode}` | `d().d` | **uploadPaceRecord** |
| `i(pathList,runRecordCode)` | `{pois,runRecordCode}` | `d().h(null,body)` | uploadRunRecord（旧，无 sign） |
| `j(pathList,runRecordCode)` | `{pois,runRecordCode}` + **sign** | `d().h(sign,body)` | **uploadRunRecord（新）** |
| `k(stepList,stepInterval,runRecordCode)` | `{stepList,stepInterval,runRecordCode}` | `d().j` | **uploadStepsRecord** |
| `l(strideList,strideInterval,runRecordCode)` | `{strideList:[{map}],strideInterval,runRecordCode}` | `d().g` | **uploadStrideRecord** |
| `m(targetPoints,runRecordCode)` | `{runRecordCode,targetPoints}` | `d().e` | **uploadPassPoint** |
| `c(params)` | 先 `mp8.f` 加 runImgRecord | `d().i` | **finishRun（finishSunRun_v2）** |

### 3. 关键方法 `j()` —— uploadRunRecord 的 sign 完整链路

```java
public Observable<BaseEntity<UploadData>> j(List<RunLatLng> pathList, String runRecordCode) {
    HashMap map = new HashMap();
    map.put("pois", pathList);
    map.put("runRecordCode", runRecordCode);
    vw9.b("RunModel", "上传日志：pathList>>" + mv3.u(pathList));     // 日志
    e58.m(map, wh7.e().g().n());                                    // 装饰公共参数（appVersion/deviceId/timestamp...）
    String jSONString = JSON.toJSONString(map, SerializerFeature.WriteMapNullValue);  // 序列化（保留 null）
    return d().h(
        cq.c(h58.c(jSONString), c23.d()),                          // sign = AES(SHA256(json)旋转, signKey)
        RequestBody.create(MediaType.parse("application/json"), jSONString)   // body = 装饰后的 json
    );
}
```

关键点：
- `e58.m(map, ...)` 装饰公共参数（与 ParamsInterceptor.decorateParams 同类逻辑）。
- `JSON.toJSONString(map, WriteMapNullValue)` —— **WriteMapNullValue 保留 null 字段**（sign 必须基于这个）。
- `sign = cq.c(h58.c(json), c23.d())` —— 与 ParamsInterceptor.getSign 完全相同的算法。

### 4. 关键方法 `l()` —— uploadStrideRecord（★strideList 外包数组）

```java
public Observable<BaseEntity<UploadData>> l(Map<String, Object> strideList, int strideInterval, String runRecordCode) {
    ArrayList arrayList = new ArrayList(1);
    arrayList.add(strideList);          // ★ strideList(Map) 外包一层 ArrayList
    HashMap map = new HashMap();
    map.put("strideList", arrayList);   // → strideList: [ {map} ]
    map.put("strideInterval", Integer.valueOf(strideInterval));
    map.put("runRecordCode", runRecordCode);
    return d().g(RequestBody.create(...JSON.toJSONString(map, WriteMapNullValue)));
}
```

> `strideList` 是 `[{map}]`（Map 外包数组）。此前模拟传扁平结构 → 服务端报「请合规跑步」的根因。
> `map` 内部 key 由 native 层（DataComponent）构造，Java 反编译不可见，待真实跑步 hook `ApiDataComponent.b0` 采集。

### 5. 关键方法 `c()` —— finishRun

```java
public Observable<BaseEntity<FinishRunResult>> c(Map<String, Object> params) {
    mp8.f(params);   // 追加 runImgRecord + timestamp（见 mp8.f）
    return d().i(RequestBody.create(...JSON.toJSONString(params)));
}
```

---

## 四、a15.java —— MD5 工具（标准 MD5，无魔改）

### 1. 字段

| 字段 | 类型 | 语义 |
|------|------|------|
| `a` | String[] | 十六进制字符表 `{"0".."9","a".."f"}`（16 个，小写） |

### 2. 方法逐行语义

| 方法 | 签名 | 语义 |
|------|------|------|
| `a(byte[])` | byte[]→String | 字节数组 → hex 字符串（逐字节调 b()） |
| `b(byte)` | byte→String | 单字节 → 2 位 hex（`i=b; if(b<0) i=b+256;` 处理有符号） |
| `c(String)` | String→String | `return d(origin, "UTF-8")` —— **MD5(UTF-8)** |
| `d(String,String)` | →String | `MessageDigest.getInstance("MD5")` → hex |

> `a15.c` = **标准 MD5 小写 hex**，无盐、无自定义魔改。`runImgRecord` 里的图片项与整体拼接后都走这个标准 MD5。

---

## 五、四类协同的完整数据流（一次结束跑步）

```
StopRunUtils.q 组装 finish body（runRecordCode/duration/distance/totalStep/...）
   │
   ├─> mp8.f(body)                          ← mp8.java
   │      body["timestamp"]  = now + z70.B()
   │      body["runImgRecord"] = a15.c(      ← a15.java (MD5)
   │            runRecordCode + "260826158.6.8"
   │            + k14.a.c(hcj_bg_run_index)   ← K.b2s 图片派生值（native）
   │            + timestamp )
   │
   └─> qf7.c(body)                          ← qf7.java
          d().i(finishSunRun_v2, body)

跑步过程上传：
  qf7.j(pois)  → sign = cq.c(h58.c(json), c23.d())   ← c23.java (signKey) + AES
  qf7.l(strideList) → strideList:[{map}]
  qf7.h(pace) / qf7.k(step) / qf7.m(targetPoints)

每个 HTTP 请求：
  EncryptInterceptor  用 c23.b() (encKey) 加密敏感字段
  ParamsInterceptor.getSign 用 c23.d() (signKey) 算 sign
```

---

## 六、动态实测印证（2026-09-07）

| 结论 | 印证方式 |
|------|---------|
| encKey = `F44B0282BEA83557` | 响应 `phone` 密文解密 = `13407006275` ✓ |
| signKey = `F44B0282BEA83557` | 4 个接口 code=0（sign 校验通过）✓ |
| `a15.c` = 标准 MD5 | 源码 `MessageDigest.getInstance("MD5")` |
| 四类运行时为"类级别加密" | Frida 遍历 29 个 classLoader，c23/mp8/qf7/a15 均未加载（懒解密） |

**待真实跑步触发采集的剩余项**：
1. `K.b2s` 图片派生值（`runImgRecord` 的关键未知项）
2. `strideList` map 的内部 key（`ApiDataComponent.b0` / `qf7.l`）
