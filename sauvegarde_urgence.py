# sauvegarde_urgence.py - Script TEMPORAIRE de sauvegarde
import pandas as pd
import pickle
import os
from datetime import datetime

def sauvegarder_donnees():
    try:
        # Essayer de récupérer depuis le cache Streamlit existant
        cache_files = [
            "data_cache.pkl",
            "votre_fichier_donnees.csv",  # Remplacez par vos vrais noms de fichiers
            # Ajoutez tous les fichiers que votre app utilise
        ]
        
        for file in cache_files:
            if os.path.exists(file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{file}_{timestamp}"
                
                if file.endswith('.pkl'):
                    with open(file, 'rb') as f:
                        data = pickle.load(f)
                    data.to_csv(f"{backup_name}.csv", index=False)
                else:
                    # Copier le fichier tel quel
                    import shutil
                    shutil.copy2(file, backup_name)
                
                print(f"✅ {file} sauvegardé comme {backup_name}")
        
        print("🎉 Toutes les sauvegardes sont terminées!")
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")

if __name__ == "__main__":
    sauvegarder_donnees()
