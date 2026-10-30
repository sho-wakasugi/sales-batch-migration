package com.example.salesbatch.sales;

import org.apache.ibatis.annotations.Mapper;

/**
 * 売上テーブルの MyBatis Mapper（SQLは mapper/SalesMapper.xml）。
 * <p>
 * insert（登録）は MyBatisBatchItemWriter から、
 * selectMonthlySummary（集計）は MyBatisCursorItemReader から ID 指定で呼ぶ。
 */
@Mapper
public interface SalesMapper {

    String NAMESPACE = "com.example.salesbatch.sales.SalesMapper";
    String INSERT = NAMESPACE + ".insert";
    String SELECT_MONTHLY_SUMMARY = NAMESPACE + ".selectMonthlySummary";

    int insert(Sales sales);

    int deleteAll();

    long countAll();
}
