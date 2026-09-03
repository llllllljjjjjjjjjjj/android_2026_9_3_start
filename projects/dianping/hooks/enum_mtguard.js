// 枚举 mtguard 相关类，找 main3 所在类
Java.perform(function () {
    var found = [];
    Java.enumerateLoadedClasses({
        onMatch: function (className) {
            if (className.indexOf('mtguard') !== -1 || className.indexOf('MainBridge') !== -1) {
                found.push(className);
            }
        },
        onComplete: function () {
            send({ type: 'classes', classes: found });
        }
    });
});
