1. 4.1 只用于 failure discovery、mechanism validation 和 development ablation。
2. 在线算法不得使用 GT / EVO / APE。
3. 不得使用特定时间、位置、路线、卫星 ID 或数据集身份规则。
4. 所有用于 first solve 的 reliability evidence 必须在 first optimize() 前可获得。
5. 优先使用 normalized / dimensionless / physically interpretable evidence。
6. 数值阈值不得仅因为在 4.1 上 trajectory 指标最好而选择。
7. sensor-specific evidence 可以不同，但必须映射到统一的 reliability / confidence 语义。
8. 算法结构与参数冻结后，必须在未参与开发的 sequence/dataset 上做外部验证。
