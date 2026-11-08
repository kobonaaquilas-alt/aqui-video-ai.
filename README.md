# AQUI VIDEO AI

Générateur expérimental image-vers-vidéo basé sur Wan 2.2 via un Space public Hugging Face.

## Lancer une génération
1. Ouvrir l'onglet **Actions**.
2. Choisir **Générer une vidéo Wan 2.2**.
3. Cliquer **Run workflow**.
4. Fournir une URL publique directe vers une image JPG/PNG/WEBP et un prompt de mouvement.
5. Télécharger le MP4 dans les artefacts du workflow.

## Limites importantes
- Ce prototype anime une image fixe ; il ne crée pas encore une vidéo complète à partir du seul texte.
- Le Space public peut être en file d'attente, indisponible ou soumis à des quotas gratuits Hugging Face.
- Les générations ne sont pas illimitées et la réussite n'est pas garantie.
- Le MP4 est conservé comme artefact GitHub temporaire ; aucune publication Metricool automatique n'est configurée.
- Ne pas utiliser d'image privée ou sensible : l'image est transmise au service public tiers.

Space utilisé : https://huggingface.co/spaces/prithivMLmods/Wan2.2-Fast
