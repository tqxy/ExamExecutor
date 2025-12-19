#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF试卷分析模块
用于分析试卷结构，识别题目数量和边界
"""

import os
import cv2
import numpy as np
import pdfplumber
from PIL import Image
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFAnalyzer:
    """PDF试卷分析器"""
    
    def __init__(self, pdf_path):
        """
        初始化PDF分析器
        
        Args:
            pdf_path (str): PDF文件路径
        """
        self.pdf_path = pdf_path
        self.questions = []
        
    def pdf_to_images(self, output_dir="pdf_pages"):
        """
        将PDF转换为图像
        
        Args:
            output_dir (str): 输出目录
            
        Returns:
            list: 图像文件路径列表
        """
        logger.info("开始将PDF转换为图像...")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    logger.info(f"正在处理第 {i+1} 页...")
                    
                    # 尝试不同的转换方法
                    try:
                        # 方法1: 使用pdfplumber的to_image
                        im = page.to_image(resolution=200)
                        image_path = os.path.join(output_dir, f"page_{i+1}.png")
                        im.save(image_path)
                    except Exception as e:
                        logger.warning(f"使用to_image转换第 {i+1} 页失败: {e}")
                        # 方法2: 使用crop和to_image的组合
                        try:
                            # 获取页面尺寸
                            bbox = page.bbox
                            im = page.to_image(resolution=200)
                            image_path = os.path.join(output_dir, f"page_{i+1}.png")
                            im.save(image_path)
                        except Exception as e2:
                            logger.warning(f"使用备用方法转换第 {i+1} 页也失败: {e2}")
                            # 方法3: 创建空白图像作为占位符
                            image_path = os.path.join(output_dir, f"page_{i+1}_placeholder.png")
                            # 创建白色背景图像
                            placeholder = Image.new('RGB', (1600, 2000), color='white')
                            placeholder.save(image_path)
                            logger.info(f"为第 {i+1} 页创建了占位符图像")
                    
                    # 检查图像是否有效
                    if os.path.exists(image_path):
                        # 检查文件大小
                        file_size = os.path.getsize(image_path)
                        if file_size > 1000:  # 大于1KB认为是有效图像
                            image_paths.append(image_path)
                            logger.info(f"已保存页面 {i+1} 到 {image_path} (大小: {file_size} bytes)")
                        else:
                            logger.warning(f"页面 {i+1} 的图像文件太小 ({file_size} bytes)，可能为空白页面")
                    else:
                        logger.error(f"页面 {i+1} 的图像文件未创建成功")
                    
        except Exception as e:
            logger.error(f"PDF转换图像时出错: {e}")
            return []
            
        logger.info(f"PDF转换完成，共生成 {len(image_paths)} 张图像")
        return image_paths
    
    def detect_question_boundaries(self, image_path):
        """
        检测题目边界
        
        Args:
            image_path (str): 图像文件路径
            
        Returns:
            list: 题目边界框列表 [(x, y, w, h), ...]
        """
        logger.info(f"开始检测题目边界: {image_path}")
        
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"无法读取图像: {image_path}")
            return []
        
        # 获取图像尺寸
        height, width = image.shape[:2]
        logger.info(f"图像尺寸: {width} x {height}")
        
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 应用多种阈值处理方法
        methods = [
            ("THRESH_BINARY", cv2.THRESH_BINARY, 127),
            ("THRESH_BINARY_INV", cv2.THRESH_BINARY_INV, 127),
            ("THRESH_BINARY_HIGH", cv2.THRESH_BINARY, 200),
            ("THRESH_BINARY_INV_HIGH", cv2.THRESH_BINARY_INV, 200),
        ]
        
        all_boxes = []
        
        for method_name, method, threshold_value in methods:
            try:
                _, thresh = cv2.threshold(gray, threshold_value, 255, method)
                
                # 查找轮廓
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # 过滤轮廓，只保留较大的矩形区域
                question_boxes = []
                min_area = 3000  # 最小面积阈值
                
                for contour in contours:
                    # 计算轮廓面积
                    area = cv2.contourArea(contour)
                    
                    # 如果面积大于阈值
                    if area > min_area:
                        # 获取边界框
                        x, y, w, h = cv2.boundingRect(contour)
                        
                        # 过滤太小或太大的区域
                        if (w > 50 and h > 30 and 
                            w < width * 0.9 and h < height * 0.8):
                            # 过滤宽高比不合理的区域
                            aspect_ratio = w / h
                            if 0.3 < aspect_ratio < 10.0:  # 合理的宽高比范围
                                question_boxes.append((x, y, w, h))
                
                all_boxes.extend(question_boxes)
                logger.info(f"使用 {method_name} 方法检测到 {len(question_boxes)} 个候选区域")
                
            except Exception as e:
                logger.warning(f"使用 {method_name} 方法时出错: {e}")
        
        # 去重相似的边界框
        unique_boxes = self._remove_duplicate_boxes(all_boxes)
        
        # 按照y坐标排序
        unique_boxes.sort(key=lambda box: box[1])
        
        logger.info(f"最终检测到 {len(unique_boxes)} 个题目区域")
        return unique_boxes
    
    def _remove_duplicate_boxes(self, boxes, overlap_threshold=0.5):
        """
        去除重复的边界框
        
        Args:
            boxes (list): 边界框列表
            overlap_threshold (float): 重叠阈值
            
        Returns:
            list: 去重后的边界框列表
        """
        if len(boxes) <= 1:
            return boxes
        
        # 按面积排序，大的在前
        boxes.sort(key=lambda box: box[2] * box[3], reverse=True)
        
        unique_boxes = []
        
        for box in boxes:
            is_duplicate = False
            
            for unique_box in unique_boxes:
                # 计算重叠度
                x1, y1, w1, h1 = box
                x2, y2, w2, h2 = unique_box
                
                # 计算交集区域
                xi1, yi1 = max(x1, x2), max(y1, y2)
                xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
                
                if xi1 < xi2 and yi1 < yi2:
                    # 计算交集面积
                    intersection = (xi2 - xi1) * (yi2 - yi1)
                    # 计算最小框面积
                    min_area = min(w1 * h1, w2 * h2)
                    
                    if intersection / min_area > overlap_threshold:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_boxes.append(box)
        
        return unique_boxes
    
    def extract_questions(self, image_path, question_boxes):
        """
        从图像中提取题目
        
        Args:
            image_path (str): 图像文件路径
            question_boxes (list): 题目边界框列表
            
        Returns:
            list: 题目图像路径列表
        """
        logger.info(f"开始提取题目: {image_path}")
        
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"无法读取图像: {image_path}")
            return []
        
        # 创建题目输出目录
        questions_dir = "extracted_questions"
        os.makedirs(questions_dir, exist_ok=True)
        
        question_images = []
        
        # 提取每个题目
        for i, (x, y, w, h) in enumerate(question_boxes):
            # 裁剪题目区域
            question_img = image[y:y+h, x:x+w]
            
            # 保存题目图像
            question_path = os.path.join(questions_dir, f"question_{i+1}.png")
            cv2.imwrite(question_path, question_img)
            question_images.append(question_path)
            
            logger.info(f"已保存题目 {i+1} 到 {question_path}")
        
        logger.info(f"题目提取完成，共提取 {len(question_images)} 个题目")
        return question_images
    
    def analyze_pdf(self):
        """
        分析PDF试卷
        
        Returns:
            dict: 分析结果
        """
        logger.info("开始分析PDF试卷...")
        
        # 1. 将PDF转换为图像
        image_paths = self.pdf_to_images()
        if not image_paths:
            logger.error("PDF转换图像失败")
            return {}
        
        results = {
            "total_pages": len(image_paths),
            "pages": []
        }
        
        # 2. 分析每一页
        for i, image_path in enumerate(image_paths):
            page_info = {
                "page_number": i + 1,
                "image_path": image_path,
                "questions": []
            }
            
            # 检测题目边界
            question_boxes = self.detect_question_boundaries(image_path)
            
            # 提取题目
            question_images = self.extract_questions(image_path, question_boxes)
            
            # 记录题目信息
            for j, question_path in enumerate(question_images):
                question_info = {
                    "question_number": j + 1,
                    "image_path": question_path,
                    "bounding_box": question_boxes[j] if j < len(question_boxes) else None
                }
                page_info["questions"].append(question_info)
            
            results["pages"].append(page_info)
        
        # 统计总题目数
        total_questions = sum(len(page["questions"]) for page in results["pages"])
        results["total_questions"] = total_questions
        
        logger.info(f"PDF分析完成，共 {results['total_pages']} 页，{total_questions} 道题目")
        return results

def main():
    """主函数"""
    pdf_path = r"c:\Users\cpgongyong\Desktop\ExamExecutor\ocr_module\target\2023年考研数学（一）真题【公众号，皮皮考研】.pdf"
    
    # 创建PDF分析器
    analyzer = PDFAnalyzer(pdf_path)
    
    # 分析PDF
    results = analyzer.analyze_pdf()
    
    # 保存结果到文件
    import json
    with open("pdf_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("PDF分析完成，结果已保存到 pdf_analysis_results.json")

if __name__ == "__main__":
    main()