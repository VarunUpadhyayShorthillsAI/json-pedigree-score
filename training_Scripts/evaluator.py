import pandas as pd
import numpy as np
import supervision as sv
from ultralytics import YOLO
from tqdm import tqdm
import os

def evaluate_model(model_path, dataset_path, class_names, conf_threshold=0.3, iou_threshold=0.5):
    """
    Evaluate a YOLO model using Supervision library
    Args:
        model_path: Path to .pt weights file
        dataset_path: Path to dataset root (containing test/images, test/labels, data.yaml)
        class_names: List of class names
        conf_threshold: Confidence threshold for predictions
        iou_threshold: IoU threshold for mAP calculation
    """
    try:
        evaluation_results = {}

        # Load the detection dataset from YOLO annotations
        ds = sv.DetectionDataset.from_yolo(
            images_directory_path=os.path.join(dataset_path, "test", "images"),
            annotations_directory_path=os.path.join(dataset_path, "test", "labels"),
            data_yaml_path=os.path.join(dataset_path, "data.yaml"),
        )

        # Load model
        model = YOLO(model_path)

        def callback(image: np.ndarray) -> sv.Detections:
            result = model.predict(image, conf=conf_threshold, verbose=False)[0]
            return sv.Detections.from_ultralytics(result)

        # Run predictions
        predictions, targets = [], []
        image_names = []
        per_image_results = []
        
        print(f"\nEvaluating model: {os.path.basename(model_path)}")
        for image_path, image, labels in tqdm(ds):
            try:
                detections = callback(image)
                predictions.append(detections)
                targets.append(labels)
                
                # Store image name for per-image results
                image_name = os.path.basename(image_path)
                image_names.append(image_name)
                
                # Calculate per-image confusion matrix
                img_confusion_matrix = sv.ConfusionMatrix.from_detections(
                    predictions=[detections],
                    targets=[labels],
                    classes=ds.classes,
                    conf_threshold=conf_threshold,
                    iou_threshold=iou_threshold
                )
                
                # Per-image metrics for each class
                img_results = {'Image': image_name}
                
                # Calculate metrics for each class
                for i, class_name in enumerate(class_names):
                    if i < len(img_confusion_matrix.matrix):
                        tp = int(img_confusion_matrix.matrix[i, i])
                        fp = int(img_confusion_matrix.matrix[-1, i])
                        fn = int(img_confusion_matrix.matrix[i, -1])
                        
                        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                        
                        img_results.update({
                            f'{class_name}_TP': tp,
                            f'{class_name}_FP': fp,
                            f'{class_name}_FN': fn,
                            f'{class_name}_Precision': round(precision, 4),
                            f'{class_name}_Recall': round(recall, 4)
                        })
                
                per_image_results.append(img_results)
                
            except Exception as e:
                print(f"Error processing image {image_path}: {str(e)}")
                continue

        # Calculate overall Confusion Matrix
        confusion_matrix = sv.ConfusionMatrix.from_detections(
            predictions=predictions,
            targets=targets,
            classes=ds.classes,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold
        )

        # Calculate overall metrics for each class
        class_results = {}
        for i, class_name in enumerate(class_names):
            if i < len(confusion_matrix.matrix):
                tp = int(confusion_matrix.matrix[i, i])
                fp = int(confusion_matrix.matrix[-1, i])
                fn = int(confusion_matrix.matrix[i, -1])
                
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                
                class_results[class_name] = {
                    'TP': tp,
                    'FP': fp,
                    'FN': fn,
                    'Precision': round(precision, 4),
                    'Recall': round(recall, 4)
                }

        # Calculate mAP
        try:
            mean_average_precision = sv.MeanAveragePrecision.from_detections(
                predictions=predictions,
                targets=targets
            )
            
            # Add mAP results to class_results
            class_results['mAP'] = {
                'TP': 0,  # Placeholder values for consistency
                'FP': 0,
                'FN': 0,
                'Precision': round(mean_average_precision.map50, 4),
                'Recall': round(mean_average_precision.map50_95, 4)
            }
        except Exception as e:
            print(f"Warning: Could not calculate mAP: {str(e)}")

        evaluation_results[os.path.basename(model_path)] = class_results

        # Format results for Excel
            # Modified part of the code where we create Excel data:
        # Format results for Excel
        modified_data = []
        map_data = []
        
        for model_name, results in evaluation_results.items():
            # Separate mAP metrics
            if 'mAP' in results:
                map_metrics = results.pop('mAP')  # Remove mAP from class results
                map_data.append({
                    'Model': model_name,
                    'mAP50': map_metrics['Precision'],  # Using Precision field for mAP50
                    'mAP50-95': map_metrics['Recall']   # Using Recall field for mAP50-95
                })
            
            # Process class metrics
            for class_name, metrics in results.items():
                row = {
                    'Model': model_name,
                    'Class': class_name,
                    'TP': metrics['TP'],
                    'FP': metrics['FP'],
                    'FN': metrics['FN'],
                    'Precision': metrics['Precision'],
                    'Recall': metrics['Recall']
                }
                modified_data.append(row)

        # Save results to Excel with multiple sheets
        output_path = f"evaluation_results_{os.path.basename(model_path).split('.')[0]}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Class-wise results
            aggregated_df = pd.DataFrame(modified_data)
            aggregated_df.to_excel(writer, sheet_name='Class_Results', index=False)
            
            # Sheet 2: mAP metrics
            map_df = pd.DataFrame(map_data)
            map_df.to_excel(writer, sheet_name='mAP_Results', index=False)
            
            # Sheet 3: Per-image results
            per_image_df = pd.DataFrame(per_image_results)
            per_image_df.to_excel(writer, sheet_name='Per_Image_Results', index=False)
        
        print(f"\nResults saved to: {output_path}")
        print(f" Aggregated Results: {len(modified_data)} rows")
        print(f"  Per-Image Results: {len(per_image_results)} images evaluated")
        print(f"\nOpen the Excel file to see:")
        print(f"  - 'Aggregated_Results' sheet: Overall model performance")
        print(f"  - 'Per_Image_Results' sheet: Per-image performance")
        
        return evaluation_results, per_image_results

    except Exception as e:
        print(f"Error in evaluation: {str(e)}")
        return None, None

if __name__ == "__main__":
    #  Nodes dataset
    model_path = "/home/shorthills/projects/pedigree_vision/YOLO/nodes-model/train_long/weights/best.pt"
    dataset_path = "/home/shorthills/projects/pedigree_vision/YOLO/Shaded-Nodes-4"
    class_names = ['Female', 'Male', 'Miscarriage', 'Unknown']
    
    #Form data
    # model_path = "/home/shorthills/projects/pedigree_vision/YOLO/form_data-model/train_long/weights/best.pt"
    # dataset_path = "/home/shorthills/projects/pedigree_vision/YOLO/Form-Section-2"
    # class_names = ['form-section']

    #Generation
    # model_path = "/home/shorthills/projects/pedigree_vision/YOLO/generation-model/train_long/weights/best.pt"
    # dataset_path = "/home/shorthills/projects/pedigree_vision/YOLO/Generation-2"
    # class_names = ['Generation']
    
    #Symbol
    # model_path = "/home/shorthills/projects/pedigree_vision/YOLO/symbols-model/train_long/weights/best.pt"
    # dataset_path = "/home/shorthills/projects/pedigree_vision/YOLO/Symbols-5"
    # class_names = ['Adopted_in' ,'Adopted_out' ,'Carrier' ,'Deceased' ,'Divorce' ,'Patient' ,]




    results = evaluate_model(
        model_path=model_path,
        dataset_path=dataset_path,
        class_names=class_names,
        conf_threshold=0.5,
        iou_threshold=0.5
    )