#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF试卷分析模块
使用Pix2Text+Paddle OCR组合方案分析试卷结构，识别题目数量和边界
"""

import os
import cv2
import numpy as np
from PIL import Image
import logging

# 添加项目根目录到Python路径
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入OCR模块
try:
    from src.main import OCRProcessor
    OCR_AVAILABLE = True
    logger.info("成功导入OCR处理器")
except ImportError as e:
    OCR_AVAILABLE = False
    logger.error(f"无法导入OCR处理器: {e}")

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
        self.ocr_processor = OCRProcessor() if OCR_AVAILABLE else None
        
    def pdf_to_images(self, output_dir="pdf_pages"):
        """
        将PDF转换为图像（使用PyPDF2）
        
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
            import PyPDF2
            from pdf2image import convert_from_path
            
            # 使用pdf2image转换PDF为图像
            pages = convert_from_path(self.pdf_path, dpi=200, output_folder=output_dir, 
                                    output_file="page", fmt="png", thread_count=4)
            
            # 重命名文件以符合我们的命名规范
            for i, page in enumerate(pages):
                image_path = os.path.join(output_dir, f"page_{i+1}.png")
                if not os.path.exists(image_path):
                    page.save(image_path, "PNG")
                image_paths.append(image_path)
                logger.info(f"已保存页面 {i+1} 到 {image_path}")
                
        except ImportError:
            logger.warning("pdf2image未安装，尝试使用备用方法...")
            # 安装pdf2image后再试
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pdf2image"])
                from pdf2image import convert_from_path
                pages = convert_from_path(self.pdf_path, dpi=200, output_folder=output_dir, 
                                        output_file="page", fmt="png", thread_count=4)
                
                for i, page in enumerate(pages):
                    image_path = os.path.join(output_dir, f"page_{i+1}.png")
                    if not os.path.exists(image_path):
                        page.save(image_path, "PNG")
                    image_paths.append(image_path)
                    logger.info(f"已保存页面 {i+1} 到 {image_path}")
            except Exception as e:
                logger.error(f"PDF转换图像时出错: {e}")
                return []
        except Exception as e:
            logger.error(f"PDF转换图像时出错: {e}")
            return []
            
        logger.info(f"PDF转换完成，共生成 {len(image_paths)} 张图像")
        return image_paths
    
    def detect_question_boundaries(self, image_path):
        """
        检测题目边界（使用OCR辅助检测）
        
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
        
        # 使用OCR处理器进行文本检测
        if self.ocr_processor and OCR_AVAILABLE:
            try:
                # 对整个页面进行OCR处理
                result = self.ocr_processor.process_image(image_path)
                
                # 从OCR结果中提取文本框
                text_boxes = []
                if 'paddleocr_result' in result:
                    text_recognition = result['paddleocr_result'].get('text_recognition', {})
                    boxes = text_recognition.get('boxes', [])
                    texts = text_recognition.get('texts', [])
                    scores = text_recognition.get('scores', [])
                    
                    for box, text, score in zip(boxes, texts, scores):
                        if score > 0.5 and len(text.strip()) > 0:  # 置信度阈值
                            # 转换box格式为边界框
                            points = np.array(box)
                            x_min, y_min = np.min(points, axis=0)
                            x_max, y_max = np.max(points, axis=0)
                            w, h = x_max - x_min, y_max - y_min
                            text_boxes.append((int(x_min), int(y_min), int(w), int(h)))
                
                # 根据文本框聚类检测题目区域
                question_boxes = self._cluster_text_boxes(text_boxes, width, height)
                logger.info(f"通过OCR检测到 {len(question_boxes)} 个题目区域")
                return question_boxes
                
            except Exception as e:
                logger.warning(f"使用OCR检测题目边界时出错: {e}")
        
        # 如果OCR不可用或失败，使用传统的图像处理方法
        return self._detect_questions_traditional(image)
    
    def _cluster_text_boxes(self, text_boxes, image_width, image_height):
        """
        根据文本框聚类检测题目区域
        
        Args:
            text_boxes (list): 文本框列表
            image_width (int): 图像宽度
            image_height (int): 图像高度
            
        Returns:
            list: 题目边界框列表
        """
        if not text_boxes:
            return []
        
        # 按y坐标排序
        text_boxes.sort(key=lambda box: box[1])
        
        # 聚类相邻的文本框
        clusters = []
        current_cluster = [text_boxes[0]]
        line_height = text_boxes[0][3]  # 初始行高
        
        for i in range(1, len(text_boxes)):
            prev_box = current_cluster[-1]
            curr_box = text_boxes[i]
            
            # 计算垂直距离
            vertical_distance = curr_box[1] - (prev_box[1] + prev_box[3])
            
            # 更新行高估计
            line_height = (line_height + curr_box[3]) / 2
            
            # 如果垂直距离大于行高的1.5倍，认为是新的题目开始
            if vertical_distance > line_height * 1.5:
                # 保存当前聚类
                clusters.append(current_cluster)
                # 开始新的聚类
                current_cluster = [curr_box]
            else:
                # 添加到当前聚类
                current_cluster.append(curr_box)
        
        # 添加最后一个聚类
        clusters.append(current_cluster)
        
        # 为每个聚类生成边界框
        question_boxes = []
        for cluster in clusters:
            if len(cluster) >= 1:  # 至少要有1个文本框
                x_min = min(box[0] for box in cluster)
                y_min = min(box[1] for box in cluster)
                x_max = max(box[0] + box[2] for box in cluster)
                y_max = max(box[1] + box[3] for box in cluster)
                
                # 添加一些边距
                margin_x, margin_y = 20, 20
                x_min = max(0, x_min - margin_x)
                y_min = max(0, y_min - margin_y)
                x_max = min(image_width, x_max + margin_x)
                y_max = min(image_height, y_max + margin_y)
                
                w, h = x_max - x_min, y_max - y_min
                
                # 过滤太小的区域
                if w > 100 and h > 50:
                    question_boxes.append((x_min, y_min, w, h))
        
        return question_boxes
    
    def _detect_questions_traditional(self, image):
        """
        传统图像处理方法检测题目边界
        
        Args:
            image (numpy.ndarray): 图像数组
            
        Returns:
            list: 题目边界框列表
        """
        height, width = image.shape[:2]
        
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
        
        logger.info(f"传统方法最终检测到 {len(unique_boxes)} 个题目区域")
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
    
    def extract_questions(self, image_path, question_boxes, page_number=1):
        """
        从图像中提取题目
        
        Args:
            image_path (str): 图像文件路径
            question_boxes (list): 题目边界框列表
            page_number (int): 页码
            
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
            
            # 保存题目图像，使用页码和题目编号避免文件名冲突
            question_path = os.path.join(questions_dir, f"page_{page_number}_question_{i+1}.png")
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
            question_images = self.extract_questions(image_path, question_boxes, i + 1)
            
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