#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF分析器测试脚本
用于测试PDF试卷分析功能
"""

import os
import sys
import json
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_analyzer():
    """测试PDF分析器"""
    try:
        # 导入PDF分析器
        from pdf_analyzer import PDFAnalyzer
        
        # PDF文件路径
        pdf_path = r"c:\Users\cpgongyong\Desktop\ExamExecutor\ocr_module\target\2023年考研数学（一）真题【公众号，皮皮考研】.pdf"
        
        # 检查PDF文件是否存在
        if not os.path.exists(pdf_path):
            logger.error(f"PDF文件不存在: {pdf_path}")
            return False
        
        logger.info(f"开始测试PDF分析器，PDF路径: {pdf_path}")
        
        # 创建PDF分析器实例
        analyzer = PDFAnalyzer(pdf_path)
        
        # 分析PDF
        logger.info("开始分析PDF...")
        results = analyzer.analyze_pdf()
        
        # 检查结果
        if not results:
            logger.error("PDF分析失败，没有返回结果")
            return False
        
        # 保存结果到文件
        output_file = "test_pdf_analysis_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"PDF分析完成，结果已保存到 {output_file}")
        logger.info(f"总页数: {results.get('total_pages', 0)}")
        logger.info(f"总题目数: {results.get('total_questions', 0)}")
        
        # 打印详细信息
        for page in results.get("pages", []):
            page_num = page.get("page_number", 0)
            questions_count = len(page.get("questions", []))
            logger.info(f"第 {page_num} 页: {questions_count} 道题目")
            
            for question in page.get("questions", []):
                question_num = question.get("question_number", 0)
                image_path = question.get("image_path", "")
                logger.info(f"  题目 {question_num}: {image_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试PDF分析器时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("开始测试PDF分析器...")
    
    success = test_pdf_analyzer()
    
    if success:
        logger.info("PDF分析器测试成功完成")
    else:
        logger.error("PDF分析器测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()