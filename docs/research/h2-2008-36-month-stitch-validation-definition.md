# H2 2008 36-Month Historical-Universe Stitch Definition

Defined: 2026-09-10 JST, after H2-2008 downstream PASS and before observing any stitch result.

- immutable closed prefix: run `34354891519`, artifact `10105279657`, digest `sha256:98b33c37a2c25413d1d180b9b54d54d38fea1013e6b7c29af2f7cafea6d81d85`, coverage `2006-01..2008-06`.
- validated H2 suffix: run `34437984621`, artifact `10136871496`, digest `sha256:55285c67440abb520da0b2e7b35dff88baf108a5f0976f453d6be0f2379fe7a3`, coverage `2008-07..2008-12`.
- frozen builder blob: `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.

The stitch must copy the 30 prefix snapshots verbatim and append the six downstream-PASS suffix snapshots verbatim, in monthly order. It must not rebuild, repair, reorder, filter, rank, or otherwise alter either segment; it must not read strategy outcomes or run Stage21.
